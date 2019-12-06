import bpy

from .camera import (
    CPP_PT_active_camera_options,
    CPP_PT_active_camera_calibration,
    CPP_PT_active_camera_lens_distortion)
from .scene import (
    CPP_PT_camera_projection_painter,
    CPP_PT_path,
    CPP_PT_scene_cameras)
from .image_paint import (
    CPP_PT_options,
    CPP_PT_scene_options,
    CPP_PT_camera_options,
    CPP_PT_view_options,
    CPP_PT_camera_autocam_options,
    CPP_PT_view_projection_preview_options,
    CPP_PT_current_image_preview_options,
    CPP_PT_warnings_options,
    CPP_PT_memory_options,
    CPP_PT_current_camera,
    CPP_PT_current_camera_calibration,
    CPP_PT_current_camera_lens_distortion
)
from .context_menu import CPP_MT_camera_pie

__all__ = ["register", "unregister"]

_classes = [
    CPP_PT_active_camera_options,
    #CPP_PT_active_camera_calibration,
    #CPP_PT_active_camera_lens_distortion,

    CPP_PT_camera_projection_painter,
    CPP_PT_path,
    CPP_PT_scene_cameras,

    CPP_PT_options,
    CPP_PT_scene_options,
    CPP_PT_camera_options,
    CPP_PT_view_options,
    CPP_PT_camera_autocam_options,
    CPP_PT_view_projection_preview_options,
    CPP_PT_current_image_preview_options,
    CPP_PT_warnings_options,
    CPP_PT_memory_options,
    CPP_PT_current_camera,
    #CPP_PT_current_camera_calibration,
    #CPP_PT_current_camera_lens_distortion,

    CPP_MT_camera_pie
]

register, unregister = bpy.utils.register_classes_factory(_classes)
