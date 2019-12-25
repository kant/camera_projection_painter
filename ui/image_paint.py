# <pep8 compliant>

if "bpy" in locals():
    import importlib

    importlib.reload(template)
    importlib.reload(operators)
    importlib.reload(utils)

    del importlib
else:
    from . import template
    from .. import operators
    from .. import utils

import bpy
from bpy.types import Panel


class ImagePaintOptions:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Camera Paint"
    bl_category = "Camera Paint"
    bl_options = {'DEFAULT_CLOSED'}


class CPP_PT_camera_painter(Panel, ImagePaintOptions):
    bl_label = "Camera Paint"
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return utils.poll.tool_setup_poll(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align = False)

        scene = context.scene
        image_paint = scene.tool_settings.image_paint
        canvas = image_paint.canvas
        clone_image = image_paint.clone_image
        v3d = context.space_data

        if v3d.use_local_camera:
            col.label(text = "Current viewport use Local Camera.")
            col.label(text = "Some display options may work incorrect")

        if not scene.camera:
            col.label(text = "Scene has no camera", icon = 'ERROR')

        if not canvas:
            col.label(text = "Image Paint has no canvas", icon = 'ERROR')
        else:
            if canvas.cpp.invalid:
                col.label(text = "Image Paint canvas invalid", icon = 'ERROR')
        if not clone_image:
            col.label(text = "Image Paint has no clone image", icon = 'ERROR')
        else:
            if clone_image.cpp.invalid:
                col.label(text = "Image Paint Clone Image invalid", icon = 'ERROR')


# View Options
class CPP_PT_view_options(Panel, ImagePaintOptions):
    bl_label = "View"
    bl_parent_id = "CPP_PT_camera_painter"
    bl_options = set()
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return utils.poll.full_poll(context)

    def draw(self, context):
        pass


class CPP_PT_camera_options(bpy.types.Panel, ImagePaintOptions):
    bl_label = "Cameras"
    bl_parent_id = "CPP_PT_view_options"
    bl_options = set()
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align = False)
        scene = context.scene

        col.use_property_split = False
        col.prop(scene.cpp, "cameras_viewport_size")
        col.use_property_split = True

        ready_count = utils.draw.get_ready_preview_count()
        valid_count = len([n for n in bpy.data.images if not n.cpp.invalid])

        text = "Image previews:"
        if ready_count < valid_count:
            text = "Image previews (%d/%d ready):" % (ready_count, valid_count)

        col.label(text = text)

        col.operator("wm.previews_ensure", icon = 'FREEZE')
        col.prop(scene.cpp, "use_camera_image_previews")


class CPP_PT_view_projection_options(Panel, ImagePaintOptions):
    bl_label = "Projection"
    bl_parent_id = "CPP_PT_view_options"
    bl_order = 1

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.cpp, "use_projection_preview", text = "")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column(align = False)

        scene = context.scene
        col.enabled = scene.cpp.use_projection_preview
        col.prop(scene.cpp, "use_normal_highlight")
        col.prop(scene.cpp, "use_projection_outline")


class CPP_PT_current_image_preview_options(Panel, ImagePaintOptions):
    bl_label = "Current Image"
    bl_parent_id = "CPP_PT_view_options"
    bl_order = 2

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.cpp, "use_current_image_preview", text = "")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align = False)

        scene = context.scene

        col.enabled = scene.cpp.use_current_image_preview
        col.prop(scene.cpp, "current_image_alpha")
        col.prop(scene.cpp, "current_image_size")


# Utils
class CPP_PT_operator_options(Panel, ImagePaintOptions):
    bl_label = "Options"
    bl_parent_id = "CPP_PT_camera_painter"
    bl_options = set()
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return utils.poll.full_poll(context)

    def draw(self, context):
        pass


class CPP_PT_material_options(Panel, ImagePaintOptions):
    bl_label = "Material"
    bl_parent_id = "CPP_PT_operator_options"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return utils.poll.full_poll(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align = True)

        col.operator(
            operator = operators.CPP_OT_canvas_to_diffuse.bl_idname,
            text = "Canvas To Diffuse"
        )

        col.operator(
            operator = operators.CPP_OT_canvas_to_diffuse.bl_idname,
            text = "Diffuse To Canvas"
        ).reverse = True


class CPP_PT_camera_autocam_options(Panel, ImagePaintOptions):
    bl_label = "Auto Camera Selection"
    bl_parent_id = "CPP_PT_operator_options"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        return utils.poll.full_poll(context)

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.cpp, "use_auto_set_camera", text = "")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align = False)

        scene = context.scene

        scol = col.column()
        scol.enabled = not scene.cpp.use_auto_set_camera
        scol.operator(operator = operators.CPP_OT_set_camera_by_view.bl_idname)

        col.label(text = "Options:")

        row = col.row(align = True)
        row.prop_enum(scene.cpp, "auto_set_camera_method", 'FULL')
        row.prop_enum(scene.cpp, "auto_set_camera_method", 'DIRECTION')
        method = scene.cpp.auto_set_camera_method

        if method == 'FULL':
            col.prop(scene.cpp, "tolerance_full")
        elif method == 'DIRECTION':
            col.prop(scene.cpp, "tolerance_direction")


class CPP_PT_warnings_options(Panel, ImagePaintOptions):
    bl_label = "Warnings"
    bl_parent_id = "CPP_PT_operator_options"
    bl_order = 3

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.cpp, "use_warnings", text = "")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align = True)

        scene = context.scene

        col.enabled = scene.cpp.use_warnings

        col.prop(scene.cpp, "distance_warning")

        col.label(text = "Actions:")
        col.use_property_split = True

        col.prop(scene.cpp, "use_warning_action_draw")
        col.prop(scene.cpp, "use_warning_action_lock")
        col.prop(scene.cpp, "use_warning_action_popup")


class CPP_PT_memory_options(Panel, ImagePaintOptions):
    bl_label = "Memory Management"
    bl_parent_id = "CPP_PT_warnings_options"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align = False)

        row = col.row()
        row.label(text = "Images loaded:")
        row.label(text = "%d" % utils.draw.get_loaded_images_count())

        col.operator(operator = operators.CPP_OT_free_memory.bl_idname)


class CPP_PT_current_camera(Panel, ImagePaintOptions):
    bl_label = "Current Camera"
    bl_parent_id = "CPP_PT_operator_options"
    bl_options = set()
    bl_order = 4

    @classmethod
    def poll(cls, context):
        scene = context.scene
        camera_ob = context.scene.camera
        if not camera_ob:
            return False
        if camera_ob.type != 'CAMERA':
            return False
        return utils.poll.tool_setup_poll(context) and scene.camera

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align = False)

        scene = context.scene
        camera_ob = scene.camera

        template.camera_image(col, camera_ob, mode = 'CONTEXT')

        col.prop(scene.cpp, "use_auto_set_image")


class CPP_PT_current_camera_calibration(Panel, ImagePaintOptions):
    bl_label = "Calibration"
    bl_parent_id = "CPP_PT_current_camera"

    @classmethod
    def poll(cls, context):
        scene = context.scene
        data = scene.camera.data.cpp
        image = data.image
        return True if image else False

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        data = scene.camera.data.cpp
        layout.prop(data, "use_calibration", text = "")

    def draw(self, context):
        layout = self.layout
        template.camera_calibration(layout, context.scene.camera)


class CPP_PT_current_camera_lens_distortion(Panel, ImagePaintOptions):
    bl_label = "Lens Distortion"
    bl_parent_id = "CPP_PT_current_camera_calibration"

    def draw(self, context):
        layout = self.layout
        template.camera_lens_distortion(layout, context.scene.camera)
