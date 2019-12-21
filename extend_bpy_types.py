# <pep8 compliant>

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    StringProperty,
    PointerProperty
)

from . import icons
from . import utils


class CameraProperties(PropertyGroup):
    @property
    def available(self):
        image = self.id_data.cpp.image
        if not image:
            return False
        if image.cpp.invalid:
            return False
        return True

    image: PointerProperty(
        type = bpy.types.Image, name = "Image",
        options = {'HIDDEN'},
        description = "Image for texture paint from this camera")

    use_calibration: BoolProperty(
        name = "Calibration", default = False,
        options = {'HIDDEN'},
        description = "Use camera calibration")

    calibration_principal_point: FloatVectorProperty(
        name = "Principal Point",
        size = 2,
        default = (0.0, 0.0),
        step = 0.0001,
        precision = 6,
        subtype = 'TRANSLATION',
        unit = 'CAMERA',
        options = {'HIDDEN'},
        description = "A point at the intersection of the optical axis and the image plane."
                      "This point is referred to as the principal point or image center")

    calibration_skew: FloatProperty(
        name = "Skew",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")

    calibration_aspect_ratio: FloatProperty(
        name = "Aspect Ratio",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")

    lens_distortion_radial_1: FloatProperty(
        name = "Radial 1",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")

    lens_distortion_radial_2: FloatProperty(
        name = "Radial 2",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")

    lens_distortion_radial_3: FloatProperty(
        name = "Radial 3",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")

    lens_distortion_tangential_1: FloatProperty(
        name = "Tangential 1",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")

    lens_distortion_tangential_2: FloatProperty(
        name = "Tangential 2",
        default = 0.0, step = 0.001, precision = 6, soft_min = -1.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "")


class SceneProperties(PropertyGroup):
    @property
    def _scene(self):
        return self.id_data

    @property
    def has_camera_objects(self):
        for ob in self._scene.objects:
            if ob.type != 'CAMERA':
                continue
            return True
        return False

    @property
    def camera_objects(self):
        return (ob for ob in self._scene.objects if ob.type == 'CAMERA')

    @property
    def has_available_camera_objects(self):
        return len(list(self._scene.cpp.available_camera_objects)) != 0

    @property
    def available_camera_objects(self):
        return (ob for ob in self._scene.cpp.camera_objects if ob.data.cpp.available)

    @property
    def has_camera_objects_selected(self):
        return len(list(self._scene.cpp.selected_camera_objects)) != 0

    @property
    def selected_camera_objects(self):
        return (ob for ob in self._scene.cpp.camera_objects if ob.select_get())

    def cameras_hide_set(self, state):
        for ob in self.camera_objects:
            ob.hide_viewport = state

    def _use_auto_set_image_update(self, context):
        if self.use_auto_set_image:
            utils.common.set_clone_image_from_camera_data(context)

    def _use_camera_image_previews_update(self, context):
        if self.use_camera_image_previews:
            utils.draw.clear_image_previews()

    source_images_path: StringProperty(
        name = "Source Images Directory", subtype = 'DIR_PATH',
        description = "Path to source images used. "
                      "If image named same as object not found in packed images, "
                      "operator search images there and open them automatically")

    calibration_source_file: StringProperty(
        name = "Camera Calibration File", subtype = 'FILE_PATH',
        description = "Path to third-party application *.csv file."
                      "Used for automatic setup camera calibration parameters")

    # Tool relative
    mapping: EnumProperty(
        items = [('UV', "UV", "Standard UV Mapping", '', 0),
                 ('CAMERA', "Camera", "Camera Projection", '', 1)],
        name = "Mapping",
        default = 'UV',
        options = {'HIDDEN'},
        description = "Mapping method for source image")

    # Camera section
    use_auto_set_camera: BoolProperty(
        name = "Use Automatic Camera", default = False,
        options = {'HIDDEN'},
        description = "Automatic/User camera selection\n"
                      "Warning! Using this option with large images may be laggy")

    use_auto_set_image: BoolProperty(
        name = "Use Automatic Image", default = True,
        options = {'HIDDEN'},
        description = "Automatic/User image selection",
        update = _use_auto_set_image_update)

    auto_set_camera_method: EnumProperty(
        items = [
            ('FULL', "Full",
             "Automatic dependent to world orientation and location",
             icons.get_icon_id("autocam_full"), 0),
            ('DIRECTION', "Direction",
             "Automatic dependent to view direction only",
             icons.get_icon_id("autocam_direction"), 1)
        ],
        name = "Auto Camera Method",
        default = 'DIRECTION',
        options = {'HIDDEN'},
        description = "Method for camera selection")

    tolerance_full: FloatProperty(
        name = "Tolerance", default = 0.92, soft_min = 0.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "Sensitivity for automatic camera selection")

    tolerance_direction: FloatProperty(
        name = "Tolerance", default = 0.55, soft_min = 0.0, soft_max = 1.0,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "Sensitivity for automatic camera selection")

    cameras_viewport_size: FloatProperty(
        name = "Viewport Display Size",
        default = 1.0, soft_min = 1.0, soft_max = 5.0, step = 0.1,
        subtype = 'DISTANCE',
        options = {'HIDDEN'},
        description = "Viewport cameras display size")

    # Viewport draw
    use_projection_preview: BoolProperty(
        name = "Projection Preview", default = True,
        options = {'HIDDEN'},
        description = "Show preview of projection")

    use_projection_outline: BoolProperty(
        name = "Outline", default = True,
        options = {'HIDDEN'},
        description = "Show projection outline")

    use_normal_highlight: BoolProperty(
        name = "Normal Highlight", default = False,
        options = {'HIDDEN'},
        description = "Show stretching factor")

    use_camera_image_previews: BoolProperty(
        name = "Camera Images", default = False,
        options = {'HIDDEN'},
        description = "Display camera images in the viewport",
        update = _use_camera_image_previews_update)

    # Current image preview
    use_current_image_preview: BoolProperty(
        name = "Current Image", default = True,
        options = {'HIDDEN'},
        description = "Display currently used source image directly in the viewport")

    current_image_size: IntProperty(
        name = "Scale",
        default = 250, min = 100, soft_max = 1500,
        subtype = 'PIXEL',
        options = {'HIDDEN'},
        description = "Scale of displayed image in pixels")

    current_image_alpha: FloatProperty(
        name = "Alpha",
        default = 0.25, soft_min = 0.0, soft_max = 1.0, step = 1,
        subtype = 'FACTOR',
        options = {'HIDDEN'},
        description = "Alpha value for image")

    current_image_position: FloatVectorProperty(
        name = "Pos", size = 2,
        options = {'HIDDEN'},
        default = (0.0, 0.0), min = 0.0, max = 1.0)

    # Warnings
    use_warnings: BoolProperty(
        name = "Use warnings", default = True,
        options = {'HIDDEN'},
        description = "Show warning when paint may become laggy")

    use_warning_action_draw: BoolProperty(
        name = "Brush Preview", default = True,
        options = {'HIDDEN'},
        description = "Change brush preview when context out of"
                      "recommended parameters")

    use_warning_action_popup: BoolProperty(
        name = "Info popup", default = False,
        options = {'HIDDEN'},
        description = "Info popup when context out of recommended parameters")

    use_warning_action_lock: BoolProperty(
        name = "Lock Paint", default = True,
        options = {'HIDDEN'},
        description = "Lock paint when context out of recommended parameters")

    distance_warning: FloatProperty(
        name = "Safe Radius",
        default = 30.0, soft_min = 5, soft_max = 100,
        subtype = 'DISTANCE',
        options = {'HIDDEN'},
        description = "The radius of the brush projected onto the object \n"
                      "at which the drawing remains acceptable in terms of performance")


class ImageProperties(PropertyGroup):
    preview_check_passed: BoolProperty(
        default = False,
        options = {'HIDDEN', 'SKIP_SAVE'}
    )

    @property
    def static_size(self):
        image = self.id_data
        width, height = utils.common.get_image_static_size(image)
        return width, height

    @property
    def invalid(self):
        image = self.id_data
        size_x, size_y = image.cpp.static_size
        if size_x and size_y:
            return False
        return True


_classes = (
    CameraProperties,
    SceneProperties,
    ImageProperties,
)


def register():
    bpy.types.WindowManager.cpp_running = bpy.props.BoolProperty(default = False, options = {'SKIP_SAVE'})
    bpy.types.WindowManager.cpp_suspended = bpy.props.BoolProperty(default = False, options = {'SKIP_SAVE'})
    bpy.types.WindowManager.cpp_mouse_pos = bpy.props.IntVectorProperty(
        size = 2,
        default = (0, 0),
        options = {'SKIP_SAVE'})

    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.types.Camera.cpp = PointerProperty(type = CameraProperties)
    bpy.types.Scene.cpp = PointerProperty(type = SceneProperties)
    bpy.types.Image.cpp = PointerProperty(type = ImageProperties)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Image.cpp
    del bpy.types.Scene.cpp
    del bpy.types.Camera.cpp
    del bpy.types.WindowManager.cpp_running
    del bpy.types.WindowManager.cpp_suspended
    del bpy.types.WindowManager.cpp_mouse_pos
