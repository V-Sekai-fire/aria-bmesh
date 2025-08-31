# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
import dataclasses
import datetime
import importlib
import logging
from collections.abc import Set as AbstractSet

import bpy
from bpy.types import Context, Event, Image, Operator

from ..common.logger import get_logger

#
# `import io_scene_gltf2` is executed in a function, not here. Importing it in the
# global scope will result in an error on startup if the glTF Add-on is disabled.
#

logger = get_logger(__name__)


class WM_OT_vrm_io_scene_gltf2_disabled_warning(Operator):
    bl_label = "glTF 2.0 add-on is disabled"
    bl_idname = "wm.vrm_gltf2_addon_disabled_warning"
    bl_options: AbstractSet[str] = {"REGISTER"}

    def execute(self, _context: Context) -> set[str]:
        return {"FINISHED"}

    def invoke(self, context: Context, _event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, _context: Context) -> None:
        self.layout.label(
            text='Official add-on "glTF 2.0 format" is required. Please enable it.'
        )


def image_to_image_bytes(
    image: Image, export_settings: dict[str, object]
) -> tuple[bytes, str]:
    if bpy.app.version < (3, 6, 0):
        gltf2_blender_image = importlib.import_module(
            "io_scene_gltf2.blender.exp.gltf2_blender_image"
        )
    elif bpy.app.version < (4, 3):
        gltf2_blender_image = importlib.import_module(
            "io_scene_gltf2.blender.exp.material.extensions.gltf2_blender_image"
        )
    else:
        gltf2_blender_image = importlib.import_module(
            "io_scene_gltf2.blender.exp.material.encode_image"
        )
    export_image = gltf2_blender_image.ExportImage.from_blender_image(image)

    mime_type = "image/jpeg" if image.file_format == "JPEG" else "image/png"

    if bpy.app.version < (3, 3, 0):
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/518b6466032534c4be4a4c50ca72d37c169a5ebf/addons/io_scene_gltf2/blender/exp/gltf2_blender_image.py
        return export_image.encode(mime_type), mime_type

    if bpy.app.version < (3, 5, 0):
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/b8901bb58fa29d78bc2741cadb3f01b6d30d7750/addons/io_scene_gltf2/blender/exp/gltf2_blender_image.py
        image_bytes, _specular_color_factor = export_image.encode(mime_type)
        return image_bytes, mime_type

    # https://github.com/KhronosGroup/glTF-Blender-IO/blob/e662c281fc830d7ad3ea918d38c6a1881ee143c5/addons/io_scene_gltf2/blender/exp/gltf2_blender_image.py#L139
    image_bytes, _specular_color_factor = export_image.encode(
        mime_type, export_settings
    )
    return image_bytes, mime_type


def init_extras_export() -> None:
    try:
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/6f9d0d9fc1bb30e2b0bb019342ffe86bd67358fc/addons/io_scene_gltf2/blender/com/gltf2_blender_extras.py#L20-L21
        gltf2_blender_extras = importlib.import_module(
            "io_scene_gltf2.blender.com.gltf2_blender_extras"
        )
    except ModuleNotFoundError:
        return
    key = "vrm_addon_extension"
    if key not in gltf2_blender_extras.BLACK_LIST:
        gltf2_blender_extras.BLACK_LIST.append(key)

def init_extras_import() -> None:
    """Initialize import protection for vrm_addon_extension to prevent dictionary assignment."""
    try:
        # Try multiple possible module paths for different glTF2 addon versions
        gltf2_blender_extras = None
        module_paths = [
            "io_scene_gltf2.blender.com.gltf2_blender_extras",
            "io_scene_gltf2.blender.imp.gltf2_blender_extras", 
            "io_scene_gltf2.io.com.gltf2_io_extras",
        ]
        
        for module_path in module_paths:
            try:
                gltf2_blender_extras = importlib.import_module(module_path)
                logger.info(f"Successfully imported glTF2 extras module: {module_path}")
                break
            except ModuleNotFoundError:
                continue
        
        if gltf2_blender_extras is None:
            logger.warning("Could not find glTF2 extras module - vrm_addon_extension blacklisting may not work")
            return
            
        key = "vrm_addon_extension"
        
        # Check for different possible blacklist attribute names
        blacklist_attrs = ["BLACK_LIST", "BLACKLIST", "blacklist", "extras_blacklist"]
        blacklist_found = False
        
        for attr_name in blacklist_attrs:
            if hasattr(gltf2_blender_extras, attr_name):
                blacklist = getattr(gltf2_blender_extras, attr_name)
                if isinstance(blacklist, list):
                    if key not in blacklist:
                        blacklist.append(key)
                        logger.info(f"Added '{key}' to glTF2 {attr_name} to prevent dictionary assignment")
                    else:
                        logger.info(f"'{key}' already in glTF2 {attr_name}")
                    blacklist_found = True
                    break
        
        if not blacklist_found:
            logger.warning("Could not find glTF2 blacklist attribute - vrm_addon_extension may cause import errors")
            # Try to create our own blacklist if none exists
            if not hasattr(gltf2_blender_extras, 'BLACK_LIST'):
                gltf2_blender_extras.BLACK_LIST = [key]
                logger.info(f"Created new BLACK_LIST with '{key}' in glTF2 extras module")
            
    except Exception as e:
        logger.error(f"Error setting up glTF2 import protection: {e}")


def create_export_settings() -> dict[str, object]:
    # https://github.com/KhronosGroup/glTF-Blender-IO/blob/b9bdc358ebf41e5f14be397d0d612cc8d645a09e/addons/io_scene_gltf2/__init__.py#L1054
    loglevel = logging.INFO

    export_settings: dict[str, object] = {
        "loglevel": loglevel,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L522
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L258-L268
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L552
        "gltf_materials": True,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L120-L137
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L532
        "gltf_format": "GLB",
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L154-L168
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L533
        "gltf_image_format": "AUTO",
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L329-L333
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L569
        "gltf_extras": True,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L611-L633
        "gltf_user_extensions": [],
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L606
        "gltf_binary": bytearray(),
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L176-L184
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/67b2ed150b0eba08129b970dbe1116c633a77d24/addons/io_scene_gltf2/__init__.py#L530
        "gltf_keep_original_textures": False,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/bfe4ff8b1b5c26ba17b0531b67798376147d9fa7/addons/io_scene_gltf2/__init__.py#L273-L279
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/bfe4ff8b1b5c26ba17b0531b67798376147d9fa7/addons/io_scene_gltf2/__init__.py#L579
        "gltf_original_specular": False,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/e662c281fc830d7ad3ea918d38c6a1881ee143c5/addons/io_scene_gltf2/__init__.py#L208-L214
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/e662c281fc830d7ad3ea918d38c6a1881ee143c5/addons/io_scene_gltf2/__init__.py#L617
        "gltf_jpeg_quality": 75,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/a2eac6c4b4ef957b654b61970dc554e3803a642e/addons/io_scene_gltf2/__init__.py#L233-L240
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/a2eac6c4b4ef957b654b61970dc554e3803a642e/addons/io_scene_gltf2/__init__.py#L787
        "gltf_image_quality": 75,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/765c1bd8f59ce34d6e346147f379af191969777f/addons/io_scene_gltf2/__init__.py#L785
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/765c1bd8f59ce34d6e346147f379af191969777f/addons/io_scene_gltf2/__init__.py#L201-L208
        "gltf_add_webp": False,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/2debd75ace303f3a3b00a43e9d7a9507af32f194/addons/io_scene_gltf2/__init__.py#L941
        "exported_images": {},
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/2debd75ace303f3a3b00a43e9d7a9507af32f194/addons/io_scene_gltf2/__init__.py#L942
        "exported_texture_nodes": [],
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/2debd75ace303f3a3b00a43e9d7a9507af32f194/addons/io_scene_gltf2/__init__.py#L943
        "additional_texture_export": [],
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/2debd75ace303f3a3b00a43e9d7a9507af32f194/addons/io_scene_gltf2/__init__.py#L944
        "additional_texture_export_current_idx": 0,
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/2debd75ace303f3a3b00a43e9d7a9507af32f194/addons/io_scene_gltf2/__init__.py#L985-L986
        "gltf_unused_textures": False,
        "gltf_unused_images": False,
        # for https://github.com/KhronosGroup/glTF-Blender-IO/blob/06f0f908e883add2767fde828f52a013086a17c3/addons/io_scene_gltf2/blender/exp/material/extensions/gltf2_blender_gather_materials_emission.py#L72
        "current_paths": {},
        # for https://github.com/KhronosGroup/glTF-Blender-IO/blob/06f0f908e883add2767fde828f52a013086a17c3/addons/io_scene_gltf2/blender/exp/material/gltf2_blender_gather_materials.py#L171
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/06f0f908e883add2767fde828f52a013086a17c3/addons/io_scene_gltf2/blender/exp/gltf2_blender_gather.py#L62-L66
        "KHR_animation_pointer": {"materials": {}, "lights": {}, "cameras": {}},
    }

    if bpy.app.version < (4, 2):
        return export_settings

    if bpy.app.version < (4, 3):
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/b9bdc358ebf41e5f14be397d0d612cc8d645a09e/addons/io_scene_gltf2/__init__.py#L1270-L1271
        gltf2_io_debug = importlib.import_module("io_scene_gltf2.io.com.gltf2_io_debug")
    else:
        # https://github.com/KhronosGroup/glTF-Blender-IO/blob/8630228d9db25a57f21de36329ed0e6d76094efa/addons/io_scene_gltf2/__init__.py#L1305
        gltf2_io_debug = importlib.import_module("io_scene_gltf2.io.com.debug")
    export_settings["log"] = gltf2_io_debug.Log(loglevel)

    return export_settings


@dataclasses.dataclass
class ImportSceneGltfArguments:
    filepath: str
    import_pack_images: bool
    bone_heuristic: str
    guess_original_bind_pose: bool
    disable_bone_shape: bool


def import_scene_gltf(arguments: ImportSceneGltfArguments) -> set[str]:
    if bpy.app.version < (4, 2):
        return bpy.ops.import_scene.gltf(
            filepath=arguments.filepath,
            import_pack_images=arguments.import_pack_images,
            bone_heuristic=arguments.bone_heuristic,
            guess_original_bind_pose=arguments.guess_original_bind_pose,
        )

    return bpy.ops.import_scene.gltf(
        filepath=arguments.filepath,
        import_pack_images=arguments.import_pack_images,
        bone_heuristic=arguments.bone_heuristic,
        guess_original_bind_pose=arguments.guess_original_bind_pose,
        disable_bone_shape=arguments.disable_bone_shape,
    )


@dataclasses.dataclass
class ExportSceneGltfArguments:
    filepath: str
    check_existing: bool
    export_format: str
    export_extras: bool
    export_def_bones: bool
    export_current_frame: bool
    use_selection: bool
    use_active_scene: bool
    export_animations: bool
    export_armature_object_remove: bool
    export_rest_position_armature: bool
    export_all_influences: bool
    export_lights: bool
    export_try_sparse_sk: bool
    export_apply: bool


def __invoke_export_scene_gltf(arguments: ExportSceneGltfArguments) -> set[str]:
    if bpy.app.version < (3, 2):
        return bpy.ops.export_scene.gltf(
            filepath=arguments.filepath,
            check_existing=arguments.check_existing,
            export_format=arguments.export_format,
            export_extras=arguments.export_extras,
            export_def_bones=False,
            export_current_frame=arguments.export_current_frame,
            use_selection=arguments.use_selection,
            export_animations=arguments.export_animations,
            export_all_influences=arguments.export_all_influences,
            export_lights=arguments.export_lights,
            export_apply=arguments.export_apply,
        )

    if bpy.app.version < (3, 6):
        return bpy.ops.export_scene.gltf(
            filepath=arguments.filepath,
            check_existing=arguments.check_existing,
            export_format=arguments.export_format,
            export_extras=arguments.export_extras,
            export_def_bones=(bpy.app.version >= (3, 3)) and arguments.export_def_bones,
            export_current_frame=arguments.export_current_frame,
            use_selection=arguments.use_selection,
            use_active_scene=arguments.use_active_scene,
            export_animations=arguments.export_animations,
            export_all_influences=arguments.export_all_influences,
            export_lights=arguments.export_lights,
            export_apply=arguments.export_apply,
        )

    if bpy.app.version < (4,):
        return bpy.ops.export_scene.gltf(
            filepath=arguments.filepath,
            check_existing=arguments.check_existing,
            export_format=arguments.export_format,
            export_extras=arguments.export_extras,
            export_def_bones=arguments.export_def_bones,
            export_current_frame=arguments.export_current_frame,
            use_selection=arguments.use_selection,
            use_active_scene=arguments.use_active_scene,
            export_animations=arguments.export_animations,
            export_rest_position_armature=arguments.export_rest_position_armature,
            export_all_influences=arguments.export_all_influences,
            export_lights=arguments.export_lights,
            export_apply=arguments.export_apply,
        )

    if bpy.app.version < (4, 2):
        return bpy.ops.export_scene.gltf(
            filepath=arguments.filepath,
            check_existing=arguments.check_existing,
            export_format=arguments.export_format,
            export_extras=arguments.export_extras,
            export_def_bones=arguments.export_def_bones,
            export_current_frame=arguments.export_current_frame,
            use_selection=arguments.use_selection,
            use_active_scene=arguments.use_active_scene,
            export_animations=arguments.export_animations,
            export_rest_position_armature=arguments.export_rest_position_armature,
            export_try_sparse_sk=arguments.export_try_sparse_sk,
            export_all_influences=arguments.export_all_influences,
            export_lights=arguments.export_lights,
            export_apply=arguments.export_apply,
        )

    return bpy.ops.export_scene.gltf(
        filepath=arguments.filepath,
        check_existing=arguments.check_existing,
        export_format=arguments.export_format,
        export_extras=arguments.export_extras,
        export_def_bones=arguments.export_def_bones,
        export_current_frame=arguments.export_current_frame,
        use_selection=arguments.use_selection,
        use_active_scene=arguments.use_active_scene,
        export_animations=arguments.export_animations,
        export_armature_object_remove=arguments.export_armature_object_remove,
        export_rest_position_armature=arguments.export_rest_position_armature,
        export_try_sparse_sk=arguments.export_try_sparse_sk,
        export_all_influences=arguments.export_all_influences,
        export_lights=arguments.export_lights,
        export_apply=arguments.export_apply,
    )


def export_scene_gltf(arguments: ExportSceneGltfArguments) -> set[str]:
    try:
        return __invoke_export_scene_gltf(arguments)
    except RuntimeError:
        if not arguments.export_animations:
            raise
        logger.exception("Failed to export VRM with animations")
        # TODO: check traceback

    arguments.export_animations = False
    return __invoke_export_scene_gltf(arguments)
