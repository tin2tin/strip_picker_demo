import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty

def get_all_strips(context):
    """Retrieve all VSE strips safely across different Blender versions (4.x / 5.x)"""
    seq_editor = getattr(context.scene, "sequence_editor", None)
    if not seq_editor:
        return []
    
    # Try the newer Blender 4.4+ / 5.x property first
    if hasattr(seq_editor, "strips_all"):
        return seq_editor.strips_all
    # Fallback for older Blender versions
    elif hasattr(seq_editor, "sequences_all"):
        return seq_editor.sequences_all
    return []

class SEQUENCER_OT_ai_strip_picker(Operator):
    """Pick a strip in the VSE and perform an action on it"""
    bl_idname = "sequencer.strip_picker"
    bl_label = "Pick Strip"
    bl_description = "Click on a strip in the VSE to perform a custom action"
    bl_options = {"REGISTER", "UNDO"}
    
    action: StringProperty(
        name="Action",
        description="Action to perform on the picked strip",
        default="select"
    )

    def modal(self, context, event):
        # Allow standard navigation (pan/zoom) inside the editors during selection
        if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            # Locate the Sequencer area and its WINDOW region containing the mouse
            area, region = self.get_sequencer_area_and_region(context, event)
            
            if not area or not region:
                self.report({"WARNING"}, "Click inside an active Video Sequence Editor window")
                return {"RUNNING_MODAL"}

            # Map absolute mouse coordinates to the sequencer region coordinates
            mouse_region_x = event.mouse_x - region.x
            mouse_region_y = event.mouse_y - region.y
            
            v2d = region.view2d
            mouse_x_view, mouse_y_view = v2d.region_to_view(mouse_region_x, mouse_region_y)

            strips = get_all_strips(context)
            if not strips:
                self.report({"WARNING"}, "No strips found in sequence editor")
                context.window.cursor_modal_restore()
                return {"CANCELLED"}

            picked_strip = None
            for strip in strips:
                # Restrict target picking to only Image and Text strips
                if strip.type not in {'IMAGE', 'TEXT'}:
                    continue

                # Each channel on the VSE timeline represents a vertical height of 1.0 unit
                strip_y_min_view = strip.channel - 0.5
                strip_y_max_view = strip.channel + 0.5

                # Compare against the visual timeline bounds
                if (
                    strip.frame_final_start <= mouse_x_view < strip.frame_final_end and
                    strip_y_min_view <= mouse_y_view < strip_y_max_view
                ):
                    picked_strip = strip
                    break

            if picked_strip:
                self.perform_action(context, picked_strip)
                context.window.cursor_modal_restore()
                return {"FINISHED"}

            return {"RUNNING_MODAL"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            context.window.cursor_modal_restore()
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    def get_sequencer_area_and_region(self, context, event):
        """Finds the Sequence Editor area and WINDOW region under the mouse"""
        for area in context.screen.areas:
            if area.type == 'SEQUENCE_EDITOR':
                for region in area.regions:
                    # Ignore regions with unmapped types to minimize internal RNA warning logs
                    try:
                        r_type = region.type
                    except AttributeError:
                        continue

                    if r_type == 'WINDOW':
                        # Check if mouse is within this region's physical screen boundaries
                        if (region.x <= event.mouse_x <= region.x + region.width and
                            region.y <= event.mouse_y <= region.y + region.height):
                            return area, region
                            
        # Fallback to the first available Sequencer region if mouse is not strictly over it
        for area in context.screen.areas:
            if area.type == 'SEQUENCE_EDITOR':
                for region in area.regions:
                    try:
                        r_type = region.type
                    except AttributeError:
                        continue
                    if r_type == 'WINDOW':
                        return area, region
        return None, None

    def perform_action(self, context, strip):
        """Handle different actions on the picked strip"""
        seq_editor = context.scene.sequence_editor
        if not seq_editor:
            return

        if self.action == "select":
            # Clear previous selections
            for s in get_all_strips(context):
                s.select = False
            
            strip.select = True
            
            # Use active_strip in modern versions, active_sequence as legacy fallback
            if hasattr(seq_editor, "active_strip"):
                seq_editor.active_strip = strip
            elif hasattr(seq_editor, "active_sequence"):
                seq_editor.active_sequence = strip
                
            self.report({"INFO"}, f"Selected Strip: {strip.name}")

        elif self.action == "print_name":
            print(f"Picked Strip Name: {strip.name}")
            self.report({"INFO"}, f"Printed '{strip.name}' to terminal console")

        elif self.action == "mute":
            strip.mute = True
            self.report({"INFO"}, f"Muted Strip: {strip.name}")

        elif self.action == "unmute":
            strip.mute = False
            self.report({"INFO"}, f"Unmuted Strip: {strip.name}")

        else:
            self.report({"WARNING"}, f"Unknown action: {self.action}")

    def invoke(self, context, event):
        # Verify a Sequencer window exists on screen before initiating the picker
        has_sequencer = any(area.type == 'SEQUENCE_EDITOR' for area in context.screen.areas)
        if not has_sequencer:
            self.report({'WARNING'}, "This operator requires a Video Sequence Editor to be open on screen")
            return {"CANCELLED"}
            
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set("EYEDROPPER")
        return {"RUNNING_MODAL"}


class TEXT_PT_ai_strip_picker(Panel):
    """VSE Strip Picker Panel inside the Text Editor Sidebar"""
    bl_label = "VSE Strip Picker"
    bl_idname = "TEXT_PT_ai_strip_picker"
    bl_space_type = "TEXT_EDITOR"
    bl_region_type = "UI"
    bl_category = "Strip Picker"

    def draw(self, context):
        layout = self.layout
        
        # Guard against the absence of a visible sequencer area
        has_sequencer = any(area.type == 'SEQUENCE_EDITOR' for area in context.screen.areas)
        if not has_sequencer:
            layout.label(text="Please open a Sequencer area", icon="ERROR")
            return
            
        layout.label(text="Pick a strip to:")
        
        col = layout.column(align=True)
        col.operator("sequencer.strip_picker", text="Select Strip", icon="EYEDROPPER").action = "select"
        col.operator("sequencer.strip_picker", text="Print Name", icon="CONSOLE").action = "print_name"
        col.operator("sequencer.strip_picker", text="Mute Strip", icon="HIDE_ON").action = "mute"
        col.operator("sequencer.strip_picker", text="Unmute Strip", icon="HIDE_OFF").action = "unmute"


def register():
    bpy.utils.register_class(SEQUENCER_OT_ai_strip_picker)
    bpy.utils.register_class(TEXT_PT_ai_strip_picker)


def unregister():
    bpy.utils.unregister_class(SEQUENCER_OT_ai_strip_picker)
    bpy.utils.unregister_class(TEXT_PT_ai_strip_picker)


if __name__ == "__main__":
    register()
