# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
import secrets
import string
from typing import Optional

from bpy.types import Image

from ..common.convert import sequence_or_none
from ..common.logger import get_logger
from ..editor.bmesh_encoding.decoding import BmeshDecoder

logger = get_logger(__name__)


class glTF2ImportUserExtension:
    current_import_id: Optional[str] = None

    @classmethod
    def update_current_import_id(cls) -> str:
        import_id = "BlenderVrmAddonImport" + (
            "".join(secrets.choice(string.digits) for _ in range(10))
        )
        cls.current_import_id = import_id
        return import_id

    @classmethod
    def clear_current_import_id(cls) -> None:
        cls.current_import_id = None

    # https://github.com/KhronosGroup/glTF-Blender-IO/blob/6f9d0d9fc1bb30e2b0bb019342ffe86bd67358fc/addons/io_scene_gltf2/blender/imp/gltf2_blender_image.py#L51
    def gather_import_image_after_hook(
        self, image: object, bpy_image: object, gltf_importer: object
    ) -> None:
        if self.current_import_id is None:
            return

        if not isinstance(bpy_image, Image):
            logger.warning(
                "gather_import_image_after_hook: bpy_image is not a Image but %s",
                type(bpy_image),
            )
            return

        images = sequence_or_none(
            getattr(getattr(gltf_importer, "data", None), "images", None)
        )
        if images is None:
            logger.warning(
                "gather_import_image_after_hook:"
                " gltf_importer is unexpected structure: %s",
                gltf_importer,
            )
            return

        if image not in images:
            logger.warning(
                "gather_import_image_after_hook: %s not in %s", image, images
            )
            return

        index = images.index(image)

        bpy_image[self.current_import_id] = index

    def gather_import_mesh_before_hook(
        self, gltf_mesh: object, blender_mesh: object, gltf_importer: object
    ) -> None:
        """Hook to process EXT_bmesh_encoding during mesh import."""
        try:
            # Check if any primitives have EXT_bmesh_encoding extension
            if hasattr(gltf_mesh, 'primitives'):
                bmesh_decoder = BmeshDecoder()
                
                for primitive in gltf_mesh.primitives:
                    if hasattr(primitive, 'extensions') and primitive.extensions:
                        ext_bmesh_data = getattr(primitive.extensions, 'EXT_bmesh_encoding', None)
                        if ext_bmesh_data:
                            logger.info(f"Processing EXT_bmesh_encoding for mesh: {getattr(gltf_mesh, 'name', 'unnamed')}")
                            
                            # Convert extension data to dict format
                            extension_dict = self._convert_extension_to_dict(ext_bmesh_data)
                            
                            # Reconstruct BMesh from extension data
                            reconstructed_bmesh = bmesh_decoder.decode_gltf_extension_to_bmesh(extension_dict)
                            
                            if reconstructed_bmesh and blender_mesh:
                                # Apply reconstructed BMesh to Blender mesh
                                success = bmesh_decoder.apply_bmesh_to_blender_mesh(
                                    reconstructed_bmesh, blender_mesh
                                )
                                if success:
                                    logger.info("Successfully applied EXT_bmesh_encoding topology")
                                else:
                                    logger.warning("Failed to apply EXT_bmesh_encoding topology")
                                
                                reconstructed_bmesh.free()
                            
        except Exception as e:
            logger.error(f"Error processing EXT_bmesh_encoding during import: {e}")

    def _convert_extension_to_dict(self, ext_data: object) -> dict:
        """Convert glTF extension object to dictionary format."""
        try:
            # This is a simplified conversion - in a real implementation,
            # we'd need to handle the specific data structure from the glTF importer
            if hasattr(ext_data, '__dict__'):
                return vars(ext_data)
            elif isinstance(ext_data, dict):
                return ext_data
            else:
                # Fallback: try to extract known attributes
                result = {}
                for attr in ['vertices', 'edges', 'loops', 'faces']:
                    value = getattr(ext_data, attr, None)
                    if value is not None:
                        if hasattr(value, '__dict__'):
                            result[attr] = vars(value)
                        elif isinstance(value, (list, dict)):
                            result[attr] = value
                return result
        except Exception as e:
            logger.warning(f"Failed to convert extension data: {e}")
            return {}
