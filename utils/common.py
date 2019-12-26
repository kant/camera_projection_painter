# <pep8 compliant>

if "bpy" in locals():
    import importlib

    importlib.reload(shaders)
    importlib.reload(constants)

    del importlib
else:
    from .. import shaders
    from .. import __package__ as addon_pkg
    from .. import constants

import bpy

import gpu
import bgl
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix

import os
import io
import struct


class PropertyTracker(object):
    __slots__ = ("value",)

    def __init__(self, value = None):
        self.value = value

    def __call__(self, value = None):
        if self.value != value:
            self.value = value
            return True
        return False


# Math
def f_clamp(value: float, min_value: float, max_value: float):
    """Clamp float value"""
    return max(min(value, max_value), min_value)


def f_lerp(value0: float, value1: float, factor: float):
    """Linear interpolate float value"""
    return (value0 * (1.0 - factor)) + (value1 * factor)


# Curve
def iter_curve_values(curve_mapping, steps: int):
    curve_mapping.initialize()
    curve = list(curve_mapping.curves)[0]
    clip_min_x = curve_mapping.clip_min_x
    clip_min_y = curve_mapping.clip_min_y
    clip_max_x = curve_mapping.clip_max_x
    clip_max_y = curve_mapping.clip_max_y

    for i in range(steps):
        fac = i / steps
        pos = f_lerp(clip_min_x, clip_max_x, fac)
        value = curve.evaluate(pos)
        yield f_clamp(value, clip_min_y, clip_max_y)


# rv3d
def get_hovered_region_3d(context, mouse_position):
    mouse_x, mouse_y = mouse_position
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            header = next(r for r in area.regions if r.type == 'HEADER')
            tools = next(r for r in area.regions if r.type == 'TOOLS')  # N-panel
            ui = next(r for r in area.regions if r.type == 'UI')  # T-panel

            min_x = area.x + tools.width
            max_x = area.x + area.width - ui.width
            min_y = area.y
            max_y = area.y + area.height

            if header.alignment == 'TOP':
                max_y -= header.height
            elif header.alignment == 'BOTTOM':
                min_y += header.height

            if min_x <= mouse_x < max_x and min_y <= mouse_y < max_y:
                if len(area.spaces.active.region_quadviews) == 0:
                    return area.spaces.active.region_3d
                else:
                    # Not sure quadview support required?
                    pass


# Camera relative

def get_camera_attributes(ob):
    camera_size = ob.data.sensor_width
    matrix_world = ob.matrix_world
    camera_pos = ob.matrix_world.translation
    camera_forward = (
            camera_pos + (
            Vector([0.0, 0.0, -ob.data.lens / camera_size]) @ matrix_world.inverted().normalized()))

    print(camera_forward)

    camera_up = (Vector([0.0, 1.0, 0.0]) @ matrix_world.inverted())

    return camera_pos, camera_forward, camera_up


def set_clone_image_from_camera_data(context):
    scene = context.scene
    if scene.camera:
        camera = scene.camera.data
        image_paint = scene.tool_settings.image_paint
        if camera.cpp.available:
            image = camera.cpp.image
            if image:
                if image_paint.clone_image != image:
                    image_paint.clone_image = image


def bind_camera_image_by_name(ob, file_list):
    if ob.type == 'CAMERA':
        res = None

        for image in bpy.data.images:
            name, ext = os.path.splitext(image.name)
            if ob.name == image.name or ob.name == name:
                res = image
                break
        if not res:
            for file_path in file_list:
                file_name = bpy.path.basename(file_path)
                name, ext = os.path.splitext(file_name)

                if ob.name == file_name or ob.name == name:

                    if file_name in bpy.data.images:
                        bpy.data.images[file_name].filepath = file_path
                        res = bpy.data.images[file_path]
                    else:
                        res = bpy.data.images.load(filepath = file_path, check_existing = True)
                    break
        if res:
            if not res.cpp.invalid:
                ob.data.cpp.image = res
            return res
        ob.data.cpp.image = None


def set_camera_by_view(context, mouse_position):
    rw3d = get_hovered_region_3d(context, mouse_position)
    if not rw3d:
        return

    scene = context.scene

    method = scene.cpp.auto_set_camera_method
    cam_angles = {}

    for camera in scene.cpp.available_camera_objects:
        camera.select_set(False)
        if method == 'FULL':
            view_rotation = rw3d.view_rotation
            if camera.rotation_mode != 'QUATERNION':
                camera.rotation_mode = 'QUATERNION'
            cam_rot_quat = camera.rotation_quaternion.normalized()
            fac = abs(view_rotation.rotation_difference(cam_rot_quat).w)
            value = f_lerp(constants.AUTOCAM_MIN, constants.AUTOCAM_MAX, fac)
            if value > scene.cpp.tolerance_full:
                cam_angles[camera] = value

        elif method == 'DIRECTION':
            view_rotation = rw3d.view_rotation @ Vector((0.0, 0.0, -1.0))
            mat = camera.matrix_world
            camera_vec = -Vector((mat[0][2], mat[1][2], mat[2][2]))
            fac = camera_vec.dot(view_rotation)
            value = f_lerp(constants.AUTOCAM_MIN, constants.AUTOCAM_MAX, fac)
            if value > scene.cpp.tolerance_direction:
                cam_angles[camera] = value

    if not cam_angles:
        return

    view_loc = rw3d.view_matrix.inverted().translation
    index = 0
    if len(cam_angles) > 1:
        distances = [(view_loc - n.location).length for n in cam_angles.keys()]
        index = distances.index(min(distances))

    camera_ob = list(cam_angles.keys())[index]

    camera_ob.select_set(True)
    scene.camera = camera_ob


# Image relative

_image_size_cache = {}


def generate_preview(image):
    if not image:
        return -1

    if not image.preview.is_image_custom:
        image.preview.reload()
        if image.gl_load():
            return -1

        size_x, size_y = image.cpp.static_size
        if not (size_x and size_y):
            return

        preferences = bpy.context.preferences.addons[addon_pkg].preferences
        preview_size = preferences.render_preview_size  # bpy.app.render_preview_size

        if size_x > size_y:
            aspect_x = size_x / size_y
            aspect_y = 1.0
        elif size_y > size_x:
            aspect_x = 1.0
            aspect_y = size_x / size_y
        else:
            aspect_x = 1.0
            aspect_y = 1.0

        sx, sy = int(preview_size * aspect_x), int(preview_size * aspect_y)

        coords = ((0, 0), (1, 0), (1, 1), (0, 1))

        shader = shaders.shader.current_image
        batch = batch_for_shader(shader, 'TRI_FAN',
                                 {"pos": coords,
                                  "uv": coords})

        offscreen = gpu.types.GPUOffScreen(sx, sy)
        with offscreen.bind():
            bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix.Identity(4))

                gpu.matrix.translate((-1.0, -1.0))
                gpu.matrix.scale((2.0, 2.0))

                bgl.glActiveTexture(bgl.GL_TEXTURE0)
                bgl.glBindTexture(bgl.GL_TEXTURE_2D, image.bindcode)

                shader.bind()
                shader.uniform_int("image", 0)
                shader.uniform_float("alpha", 1.0)
                shader.uniform_bool("colorspace_srgb", (image.colorspace_settings.name == 'sRGB',))
                batch.draw(shader)

            buffer = bgl.Buffer(bgl.GL_BYTE, sx * sy * 4)
            bgl.glReadBuffer(bgl.GL_BACK)
            bgl.glReadPixels(0, 0, sx, sy, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)

        image.buffers_free()
        offscreen.free()

        image.preview.image_size = sx, sy
        pixels = [n / 255 for n in buffer]
        image.preview.image_pixels_float = pixels


def _get_image_metadata_from_bytesio(input, st_size):
    size_x, size_y = 0, 0

    data = input.read(24)

    if (st_size >= 24) and data.startswith(b'\x89PNG\r\n\x1a\n') and (data[12:16] == b'IHDR'):
        # PNG
        w, h = struct.unpack(">LL", data[16:24])
        size_x = int(w)
        size_y = int(h)

        # print("PNG")

    elif (st_size >= 2) and data.startswith(b'\377\330'):
        # JPEG
        input.seek(0)
        input.read(2)
        b = input.read(1)
        try:
            w, h = 0, 0
            while b and ord(b) != 0xDA:
                while ord(b) != 0xFF:
                    b = input.read(1)
                while ord(b) == 0xFF:
                    b = input.read(1)
                if 0xC0 <= ord(b) <= 0xC3:
                    input.read(3)
                    h, w = struct.unpack(">HH", input.read(4))
                    break
                else:
                    input.read(
                        int(struct.unpack(">H", input.read(2))[0]) - 2)
                b = input.read(1)
            if w and h:
                size_x = int(w)
                size_y = int(h)
        except:
            pass

    else:
        pass

    return size_x, size_y


def get_image_static_size(image):
    if image in _image_size_cache:
        return _image_size_cache[image]

    size_x, size_y = 0, 0

    if image.source == 'FILE':
        if image.packed_file:
            packed_data = image.packed_file.data
            st_size = image.packed_file.size
            with io.BytesIO(packed_data) as io_bytes:
                size_x, size_y = _get_image_metadata_from_bytesio(io_bytes, st_size)
        else:
            file_path = bpy.path.abspath(image.filepath)
            if os.path.isfile(file_path):
                st_size = os.path.getsize(file_path)
                with io.open(file_path, "rb") as io_bytes:
                    size_x, size_y = _get_image_metadata_from_bytesio(io_bytes, st_size)

    elif image.source == 'GENERATED':
        size_x, size_y = image.generated_width, image.generated_height

    if size_x and size_y:
        _image_size_cache[image] = size_x, size_y
        return size_x, size_y

    size_x, size_y = image.size[:]
    if size_x and size_y:
        _image_size_cache[image] = size_x, size_y
        return size_x, size_y
    return 0, 0


# Warnings

def ray_cast(context, mpos):
    ob = context.active_object
    scene = context.scene
    region = context.region
    rv3d = context.region_data

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, mpos)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mpos)

    ray_target = ray_origin + view_vector

    # get the ray relative to the object
    matrix_inv = ob.matrix_world.inverted()
    ray_origin_obj = matrix_inv @ ray_origin
    ray_target_obj = matrix_inv @ ray_target
    ray_direction_obj = ray_target_obj - ray_origin_obj

    # cast the ray
    success, location, normal, face_index = ob.ray_cast(ray_origin_obj, ray_direction_obj)

    if success:
        location = ob.matrix_world @ location
        distance = (ray_origin - location).length
        return distance
    return -1


def _get_check_pattern():
    from math import radians
    pattern = []
    p0 = Vector((1.0, 0.0, 0.0))
    for i in range(8):
        angle = radians(45 * i)
        mat_rotation = Matrix.Rotation(angle, 3, 'Z')
        p1 = p0.copy()
        p1.rotate(mat_rotation)
        pattern.append(p1.to_2d())
    pattern.append(Vector((0.0, 0.0)))
    return pattern


CHECK_PATTERN = _get_check_pattern()  # do it at stage of import, it's constant


def get_warning_status(context, mpos):
    mpos = Vector(mpos)

    scene = context.scene
    region = context.region
    rv3d = context.region_data

    brush_radius = scene.tool_settings.unified_paint_settings.size

    p0 = view3d_utils.region_2d_to_vector_3d(region, rv3d, mpos)
    p1 = view3d_utils.region_2d_to_vector_3d(region, rv3d, (mpos[0] + brush_radius, mpos[1]))
    scr_radius = (p0 - p1).length

    lens = context.space_data.lens * 0.01  # convert to meters

    distances = []
    for p in CHECK_PATTERN:
        ppos = mpos + (p * brush_radius)
        dist = ray_cast(context, ppos)
        if dist != -1:
            distances.append(dist)

    distance = 0.0
    if distances:
        distance = sum(distances) / len(distances)

    if distance != -1:
        a = scr_radius
        b = lens
        tan_a = a / b
        unprojected_radius = tan_a * distance
        if unprojected_radius > scene.cpp.distance_warning:
            return True

    return False


def danger_zone_popup_menu(self, context):
    layout = self.layout

    layout.emboss = 'NONE'

    scene = context.scene

    layout.label(text = "Safe Options:")
    layout.separator()
    row = layout.row()

    col = row.column()
    col.label(text = "Unprojected Radius:")

    col = row.column()
    col.emboss = 'NORMAL'
    col.label(text = "%d %s" % (
        scene.cpp.distance_warning,
        str(scene.unit_settings.length_unit).capitalize()))


# Material

def get_active_output_node(nodes):
    for node in nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial":
            if node.is_active_output:
                return node


def recursive_search_tex(nodes, active_output):
    _node = active_output
    _index = 0
    _socket = None
    _cou = len(nodes)
    while _cou:
        if _node.bl_idname == "ShaderNodeTexImage":
            break
        for i, socket in enumerate(_node.inputs):
            if socket.bl_idname in ("NodeSocketColor", "NodeSocketShader"):
                if socket.is_linked:
                    _node = socket.links[0].from_node
                else:
                    _socket = socket
                    _index = i
                break
        _cou += -1

    return _node, _socket, _index, _cou


def set_canvas_to_material_diffuse(material, image):
    material.use_nodes = True
    node_tree = material.node_tree
    nodes = node_tree.nodes

    # get active output
    active_output = get_active_output_node(nodes)
    if not active_output:
        active_output = node_tree.nodes.new(type = "ShaderNodeOutputMaterial")

    _node, _socket, _index, _cou = recursive_search_tex(nodes, active_output)

    if _node.bl_idname != "ShaderNodeTexImage" and _socket:
        node_frame = None
        for n in nodes:
            if n.label == constants.NODE_FRAME_TEXT:
                node_frame = n
        if not node_frame:
            node_frame = node_tree.nodes.new(type = "NodeFrame")

        node_frame.label = constants.NODE_FRAME_TEXT
        node_frame.use_custom_color = True
        node_frame.color = constants.NODE_FRAME_COLOR
        node_frame.select = False

        def _add_node(type, next_node, index):
            new_node = node_tree.nodes.new(type = type)
            loc = Vector(next_node.location) - Vector([new_node.width + constants.SPACE_BEETWEEN_NODES, 0])
            new_node.location = loc
            new_node.parent = node_frame
            new_node.select = False
            node_tree.links.new(new_node.outputs[0], next_node.inputs[index])
            return new_node

        if _socket.bl_idname == "NodeSocketShader":
            bsdf_node = _add_node("ShaderNodeBsdfPrincipled", _node, _index)

            _node = bsdf_node
            _index = 0
            _socket = [i for i in bsdf_node.inputs if i.bl_idname == "NodeSocketColor"][0]

        if _socket.bl_idname == "NodeSocketColor":
            tex_image_node = _add_node("ShaderNodeTexImage", _node, _index)

            _node = tex_image_node

    if _node.bl_idname == "ShaderNodeTexImage":
        _node.image = image


def set_material_diffuse_to_canvas(image_paint, material):
    node_tree = material.node_tree
    nodes = node_tree.nodes

    active_output = get_active_output_node(nodes)
    if not active_output:
        return 1
    _node, _socket, _index, _cou = recursive_search_tex(nodes, active_output)

    if _node.bl_idname == "ShaderNodeTexImage":
        image = _node.image
        if image:
            if not image.cpp.invalid:
                image_paint.canvas = image
                return -1
            else:
                return 2
    return 3
