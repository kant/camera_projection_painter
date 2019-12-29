# <pep8 compliant>

if "bpy" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(utils)
    importlib.reload(icons)

    del importlib
else:
    from .. import operators
    from .. import utils
    from .. import icons

import bpy
import re


def camera_image(layout, camera_ob, mode = 'CONTEXT'):
    layout.use_property_split = True
    layout.use_property_decorate = False

    camera = camera_ob.data

    col = layout.column(align = True)

    image = camera.cpp.image
    if image:
        col.template_ID_preview(camera.cpp, "image", open = "image.open", rows = 3, cols = 8)
    else:
        col.template_ID(camera.cpp, "image", open = "image.open")

    col.label(text = "Binding History:")

    row = col.row(align = False)

    row.template_list(
        "DATA_UL_bind_history_item", "",
        camera_ob.data, "cpp_bind_history",
        camera_ob.data.cpp, "active_bind_index",
        rows = 1)

    if mode in ('CONTEXT', 'TMP'):
        row.operator(
            operator = operators.CPP_OT_bind_history_remove.bl_idname,
            text = "", icon = "REMOVE"
        ).mode = mode

    col.separator()

    if mode == 'CONTEXT':
        operator = col.operator(
            operator = operators.CPP_OT_bind_camera_image.bl_idname,
            icon_value = icons.get_icon_id("bind_image"))
        operator.mode = mode

    if image:
        if not image.cpp.invalid:
            width, height = image.cpp.static_size
            depth = image.depth
            colorspace = image.colorspace_settings.name
            row = col.row()
            if mode == 'CONTEXT':
                row.label(text = "Width:")
                row.label(text = "%d px" % width)

                row = col.row()
                row.label(text = "Height:")
                row.label(text = "%d px" % height)

                row = col.row()
                row.label(text = "Pixel Format:")
                row.label(text = "%d-bit %s" % (depth, colorspace))
            #else:
                #row.label(text = "%dx%d %d-bit %s" % (width, height, depth, colorspace))

        else:
            col.label(text = "Invalid image", icon = 'ERROR')


def camera_calibration(layout, camera_ob):
    layout.use_property_decorate = False

    col = layout.column(align = True)

    data = camera_ob.data

    col.enabled = data.cpp.use_calibration

    col.use_property_split = True
    col.prop(data, "lens")
    col.separator()
    layout.use_property_split = False
    col.prop(data.cpp, "calibration_principal_point")
    col.separator()

    col.use_property_split = True
    col.prop(data.cpp, "calibration_skew")
    col.prop(data.cpp, "calibration_aspect_ratio")


def camera_lens_distortion(layout, camera_ob):
    layout.use_property_decorate = False
    layout.use_property_split = True

    col = layout.column(align = True)

    data = camera_ob.data

    col.enabled = data.cpp.use_calibration

    col.prop(data.cpp, "lens_distortion_radial_1")
    col.prop(data.cpp, "lens_distortion_radial_2")
    col.prop(data.cpp, "lens_distortion_radial_3")
    col.prop(data.cpp, "lens_distortion_tangential_1")
    col.prop(data.cpp, "lens_distortion_tangential_2")


def path_with_ops(layout, scene):
    layout.use_property_split = False
    layout.use_property_decorate = False
    col = layout.column(align = False)

    col.label(text = "Source Images Directory:")
    col.prop(scene.cpp, "source_images_path", text = "", icon = 'IMAGE')
    scol = col.column()
    scol.enabled = scene.cpp.has_camera_objects
    operator = scol.operator(
        operator = operators.CPP_OT_bind_camera_image,
        text = "Bind All",
        icon_value = icons.get_icon_id("bind_image"))
    operator.mode = 'ALL'

    col.separator()

    # col.prop(scene.cpp, "calibration_source_file", text = "", icon = 'FILE_CACHE')
    # col.operator(operators.CPP_OT_set_camera_calibration_from_file.bl_idname,
    #             icon_value = get_icon_id("calibration"))
