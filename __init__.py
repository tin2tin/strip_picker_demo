import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty

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
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            area = context.area
            region = context.region
            mouse_region_coord = (event.mouse_region_x, event.mouse_region_y)
            if area.type != "SEQUENCE_EDITOR" or not region:
                    self.report({"WARNING"}, "Invalid region or area for VSE")
                    context.window.cursor_modal_restore()
                    return {"CANCELLED"}

            v2d = region.view2d
            mouse_x_view, mouse_y_view = v2d.region_to_view(*mouse_region_coord)

            for strip in context.scene.sequence_editor.sequences_all:
                # Calculate the vertical bounds of the strip in view space
                # Assuming each channel has a nominal height of 1.0 in view space
                strip_y_min_view = strip.channel - 0.5 * strip.transform.scale_y  # Consider the scaled height
                strip_y_max_view = strip.channel + 0.5 * strip.transform.scale_y

                if (
                    strip.frame_start <= mouse_x_view < strip.frame_final_end and
                    strip_y_min_view <= mouse_y_view < strip_y_max_view
                ):
                    self.perform_action(context, strip)
                    context.window.cursor_modal_restore()
                    return {"FINISHED"}

            # If no strip picked, don't exit — allow continuous clicking
            return {"RUNNING_MODAL"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            context.window.cursor_modal_restore()
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    def perform_action(self, context, strip):
        """Handle different actions on the picked strip"""
        if self.action == "select":
            context.scene.sequence_editor.active_strip = strip
            self.report({"INFO"}, f"Selected: {strip.name}")

        elif self.action == "print_name":
            print(f"Picked Strip Name: {strip.name}")
            self.report({"INFO"}, f"Printed '{strip.name}' to console")

        elif self.action == "mute":
            strip.mute = True
            self.report({"INFO"}, f"Muted: {strip.name}")

        elif self.action == "unmute":
            strip.mute = False
            self.report({"INFO"}, f"Unmuted: {strip.name}")

        else:
            self.report({"WARNING"}, f"Unknown action: {self.action}")

    def invoke(self, context, event):
        if context.area.type == 'SEQUENCE_EDITOR':
            context.window_manager.modal_handler_add(self)
            context.window.cursor_modal_set("EYEDROPPER")
            return {"RUNNING_MODAL"}
        else:
            self.report({'WARNING'}, "This operator only works in the Video Sequence Editor")
            return {"CANCELLED"}


class SEQUENCER_PT_ai_strip_picker(Panel):
    """Header Panel with Action Buttons"""
    bl_label = "VSE Strip Picker"
    #bl_label = "Pallaidium"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Generative AI"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Pick a strip to:")
        row = layout.row(align=True)
        row.operator("sequencer.strip_picker", text="Select", icon="EYEDROPPER").action = "select"
        row.operator("sequencer.strip_picker", text="Print Name", icon="CONSOLE").action = "print_name"
        row.operator("sequencer.strip_picker", text="Mute", icon="HIDE_ON").action = "mute"
        row.operator("sequencer.strip_picker", text="Unmute", icon="HIDE_OFF").action = "unmute"


def register():
    bpy.utils.register_class(SEQUENCER_OT_ai_strip_picker)
    bpy.utils.register_class(SEQUENCER_PT_ai_strip_picker)


def unregister():
    bpy.utils.unregister_class(SEQUENCER_OT_ai_strip_picker)
    bpy.utils.unregister_class(SEQUENCER_PT_ai_strip_picker)


if __name__ == "__main__":
    register()
