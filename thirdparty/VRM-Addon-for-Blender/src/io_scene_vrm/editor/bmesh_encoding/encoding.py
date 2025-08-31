# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""EXT_bmesh_encoding hybrid encoding algorithms."""

from typing import Any, Dict, List, Optional, Tuple, Union

import bmesh
import bpy
from bmesh.types import BMesh, BMFace, BMLoop, BMVert, BMEdge
from mathutils import Vector

from ...common.logger import get_logger

logger = get_logger(__name__)


class BmeshEncoder:
    """Handles hybrid BMesh encoding for EXT_bmesh_encoding extension."""

    def __init__(self, use_buffer_format: bool = True, buffer_threshold: int = 1000):
        self.use_buffer_format = use_buffer_format
        self.buffer_threshold = buffer_threshold
        self.preserve_manifold_info = True

    def encode_bmesh_to_gltf_extension(self, bm: BMesh) -> Dict[str, Any]:
        """
        Encode BMesh to EXT_bmesh_encoding extension data.
        
        Returns both implicit (triangle fan) and explicit (BMesh topology) data.
        """
        if not bm.faces:
            return {}

        # Ensure face indices are valid
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.loops.ensure_lookup_table()

        vertex_count = len(bm.verts)
        use_buffers = self.use_buffer_format and vertex_count >= self.buffer_threshold

        if use_buffers:
            return self._encode_to_buffer_format(bm)
        else:
            return self._encode_to_json_format(bm)

    def _encode_to_json_format(self, bm: BMesh) -> Dict[str, Any]:
        """Encode BMesh to JSON format for small meshes."""
        extension_data = {}

        # Encode vertices
        vertices = []
        for vert in bm.verts:
            vertex_data = {
                "id": vert.index,
                "position": list(vert.co),
                "edges": [edge.index for edge in vert.link_edges],
            }
            # Add custom attributes if any
            if hasattr(vert, "custom_data"):
                vertex_data["attributes"] = vert.custom_data
            vertices.append(vertex_data)
        extension_data["vertices"] = vertices

        # Encode edges
        edges = []
        for edge in bm.edges:
            edge_data = {
                "id": edge.index,
                "vertices": [edge.verts[0].index, edge.verts[1].index],
                "faces": [face.index for face in edge.link_faces],
            }
            
            # Add manifold status if enabled
            if self.preserve_manifold_info:
                edge_data["manifold"] = self._calculate_edge_manifold_status(edge)
            
            # Add custom attributes if any
            if hasattr(edge, "custom_data"):
                edge_data["attributes"] = edge.custom_data
            edges.append(edge_data)
        extension_data["edges"] = edges

        # Encode loops
        loops = []
        loop_index = 0
        for face in bm.faces:
            face_loops = list(face.loops)
            for i, loop in enumerate(face_loops):
                next_loop_idx = loop_index + ((i + 1) % len(face_loops))
                prev_loop_idx = loop_index + ((i - 1) % len(face_loops))
                
                # Find radial navigation (loops around the same edge)
                radial_next, radial_prev = self._find_radial_loops(loop, loop_index)
                
                loop_data = {
                    "id": loop_index,
                    "vertex": loop.vert.index,
                    "edge": loop.edge.index,
                    "face": loop.face.index,
                    "next": next_loop_idx,
                    "prev": prev_loop_idx,
                    "radial_next": radial_next,
                    "radial_prev": radial_prev,
                }
                
                # Add UV coordinates if available
                if bm.loops.layers.uv:
                    uv_layer = bm.loops.layers.uv.active
                    if uv_layer:
                        loop_data["attributes"] = {
                            "TEXCOORD_0": list(loop[uv_layer].uv)
                        }
                
                loops.append(loop_data)
                loop_index += 1
                
        extension_data["loops"] = loops

        # Encode faces
        faces = []
        for face in bm.faces:
            face_data = {
                "id": face.index,
                "vertices": [vert.index for vert in face.verts],
                "edges": [edge.index for edge in face.edges],
                "loops": [loop_index + i for i in range(len(face.loops))],
                "normal": list(face.normal),
            }
            
            # Add material index (use standard glTF approach)
            if hasattr(face, "material_index"):
                face_data["materialIndex"] = face.material_index
            
            faces.append(face_data)
            loop_index += len(face.loops)

        extension_data["faces"] = faces

        return extension_data

    def _encode_to_buffer_format(self, bm: BMesh) -> Dict[str, Any]:
        """Encode BMesh to buffer format for large meshes."""
        # For now, we'll implement JSON format and add buffer support later
        # This is a placeholder for the buffer-based encoding
        logger.warning("Buffer format not yet implemented, falling back to JSON format")
        return self._encode_to_json_format(bm)

    def _calculate_edge_manifold_status(self, edge: BMEdge) -> Optional[bool]:
        """
        Calculate manifold status for an edge.
        Returns:
        - True: Confirmed manifold (exactly 2 faces, proper orientation)
        - False: Confirmed non-manifold (not exactly 2 faces)
        - None: Unknown status (not calculated)
        """
        if not self.preserve_manifold_info:
            return None
        
        linked_faces = list(edge.link_faces)
        
        # Non-manifold if not exactly 2 faces
        if len(linked_faces) != 2:
            return False
            
        # For 2 faces, check if they form a proper manifold
        # This is a simplified check - full manifold validation would be more complex
        return True

    def _find_radial_loops(self, loop: BMLoop, current_loop_index: int) -> Tuple[int, int]:
        """Find radial next/previous loops around the same edge."""
        # This is a simplified implementation
        # In a full implementation, we'd traverse all loops around the edge
        # For now, return self-references as placeholder
        return current_loop_index, current_loop_index

    def encode_triangle_fan_implicit(self, bm: BMesh) -> List[Tuple[int, Tuple[BMLoop, ...]]]:
        """
        Enhanced triangle fan encoding for EXT_bmesh_encoding.
        
        This implements the hybrid approach:
        1. Creates triangle fans that preserve BMesh topology reconstruction
        2. Uses enhanced anchor selection for better reconstruction
        3. Compatible with the explicit topology data
        """
        if not bm.faces:
            return []

        # Ensure face indices are valid
        bm.faces.ensure_lookup_table()
        
        # Sort faces by material index for better grouping
        sorted_faces = sorted(bm.faces, key=lambda f: getattr(f, 'material_index', 0))
        
        triangulated_faces = []
        prev_anchor_index = -1
        
        for face in sorted_faces:
            face_loops = list(face.loops)
            material_index = getattr(face, 'material_index', 0)
            
            if len(face_loops) <= 3:
                # Triangle or less - handle directly
                if len(face_loops) == 3:
                    # Avoid same anchor as previous face if possible
                    if face_loops[0].vert.index == prev_anchor_index and len(face_loops) > 1:
                        # Rotate to use different anchor
                        face_loops = [face_loops[1], face_loops[2], face_loops[0]]
                    
                    triangulated_faces.append((material_index, tuple(face_loops)))
                    prev_anchor_index = face_loops[0].vert.index
                continue
            
            # N-gon - create triangle fan
            # Enhanced anchor selection for better BMesh reconstruction
            anchor_candidates = [loop.vert.index for loop in face_loops]
            
            # Choose anchor different from previous if possible
            if prev_anchor_index in anchor_candidates and len(anchor_candidates) > 1:
                anchor_candidates.remove(prev_anchor_index)
            
            # Select minimum index as anchor (deterministic)
            anchor_vert_index = min(anchor_candidates)
            
            # Find anchor loop
            anchor_loop_idx = next(
                i for i, loop in enumerate(face_loops) 
                if loop.vert.index == anchor_vert_index
            )
            
            # Create triangle fan from anchor
            for i in range(2, len(face_loops)):
                v1_idx = (anchor_loop_idx + i - 1) % len(face_loops)
                v2_idx = (anchor_loop_idx + i) % len(face_loops)
                
                triangle_loops = (
                    face_loops[anchor_loop_idx],
                    face_loops[v1_idx], 
                    face_loops[v2_idx]
                )
                
                triangulated_faces.append((material_index, triangle_loops))
            
            prev_anchor_index = anchor_vert_index

        return triangulated_faces

    @staticmethod
    def create_bmesh_from_mesh(mesh_obj: bpy.types.Object) -> Optional[BMesh]:
        """Create BMesh from Blender mesh object."""
        if mesh_obj.type != 'MESH' or not mesh_obj.data:
            return None
        
        bm = bmesh.new()
        
        try:
            # Apply modifiers if needed
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = mesh_obj.evaluated_get(depsgraph)
            
            bm.from_mesh(eval_obj.data)
            bm.transform(mesh_obj.matrix_world)
            
            # Ensure indices are valid
            bm.faces.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            
            return bm
            
        except Exception as e:
            logger.error(f"Failed to create BMesh from {mesh_obj.name}: {e}")
            bm.free()
            return None
