# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""EXT_bmesh_encoding import and decoding algorithms."""

from typing import Any, Dict, List, Optional, Tuple

import bmesh
import bpy
from bmesh.types import BMesh, BMFace, BMLoop, BMVert, BMEdge
from mathutils import Vector

from ...common.logger import get_logger

logger = get_logger(__name__)


class BmeshDecoder:
    """Handles BMesh reconstruction from EXT_bmesh_encoding extension data."""

    def __init__(self):
        pass

    def decode_gltf_extension_to_bmesh(self, extension_data: Dict[str, Any]) -> Optional[BMesh]:
        """
        Decode EXT_bmesh_encoding extension data to BMesh.
        
        Supports both explicit reconstruction and implicit triangle fan fallback.
        """
        if not extension_data:
            return None

        try:
            # Check if we have explicit BMesh topology data
            if self._has_explicit_topology_data(extension_data):
                return self._reconstruct_from_explicit_data(extension_data)
            else:
                # Fallback to implicit reconstruction from triangle fans
                logger.info("EXT_bmesh_encoding: Using implicit reconstruction fallback")
                return None  # Let standard glTF import handle it
                
        except Exception as e:
            logger.error(f"Failed to decode EXT_bmesh_encoding: {e}")
            return None

    def _has_explicit_topology_data(self, extension_data: Dict[str, Any]) -> bool:
        """Check if extension data contains explicit BMesh topology."""
        required_keys = ["vertices", "edges", "loops", "faces"]
        return all(key in extension_data for key in required_keys)

    def _reconstruct_from_explicit_data(self, extension_data: Dict[str, Any]) -> Optional[BMesh]:
        """Reconstruct BMesh from explicit topology data."""
        bm = bmesh.new()
        
        try:
            vertex_data = extension_data.get("vertices", [])
            edge_data = extension_data.get("edges", [])
            loop_data = extension_data.get("loops", [])
            face_data = extension_data.get("faces", [])

            # Handle both JSON format (small meshes) and buffer format (large meshes)
            if isinstance(vertex_data, list):
                return self._reconstruct_from_json_format(
                    bm, vertex_data, edge_data, loop_data, face_data
                )
            elif isinstance(vertex_data, dict) and "count" in vertex_data:
                return self._reconstruct_from_buffer_format(
                    bm, extension_data
                )
            else:
                logger.warning("Unknown EXT_bmesh_encoding format")
                bm.free()
                return None

        except Exception as e:
            logger.error(f"Failed to reconstruct BMesh from explicit data: {e}")
            bm.free()
            return None

    def _reconstruct_from_json_format(
        self, 
        bm: BMesh, 
        vertex_data: List[Dict],
        edge_data: List[Dict],
        loop_data: List[Dict],
        face_data: List[Dict]
    ) -> BMesh:
        """Reconstruct BMesh from JSON format explicit data."""
        
        # Create vertices
        vertex_map = {}
        for vert_info in vertex_data:
            vert_id = vert_info["id"]
            position = vert_info["position"]
            vert = bm.verts.new(position)
            vertex_map[vert_id] = vert

        # Ensure vertex indices are valid
        bm.verts.ensure_lookup_table()

        # Create edges
        edge_map = {}
        for edge_info in edge_data:
            edge_id = edge_info["id"]
            vertices = edge_info["vertices"]
            
            if len(vertices) == 2:
                vert1 = vertex_map.get(vertices[0])
                vert2 = vertex_map.get(vertices[1])
                
                if vert1 and vert2:
                    try:
                        edge = bm.edges.new([vert1, vert2])
                        edge_map[edge_id] = edge
                    except ValueError:
                        # Edge already exists, find it
                        for existing_edge in bm.edges:
                            if set(existing_edge.verts) == {vert1, vert2}:
                                edge_map[edge_id] = existing_edge
                                break

        # Ensure edge indices are valid  
        bm.edges.ensure_lookup_table()

        # Create faces
        face_map = {}
        for face_info in face_data:
            face_id = face_info["id"]
            vertices = face_info["vertices"]
            
            face_verts = []
            for vert_id in vertices:
                vert = vertex_map.get(vert_id)
                if vert:
                    face_verts.append(vert)
            
            if len(face_verts) >= 3:
                try:
                    face = bm.faces.new(face_verts)
                    face_map[face_id] = face
                    
                    # Set face normal if provided
                    if "normal" in face_info:
                        face.normal = Vector(face_info["normal"])
                    
                    # Set material index if provided
                    if "materialIndex" in face_info:
                        face.material_index = face_info["materialIndex"]
                    
                except ValueError as e:
                    logger.warning(f"Failed to create face {face_id}: {e}")

        # Ensure face indices are valid
        bm.faces.ensure_lookup_table()

        # Set up UV coordinates from loop data
        if loop_data and bm.loops.layers.uv.active is None:
            # Create UV layer if it doesn't exist
            bm.loops.layers.uv.new()
        
        uv_layer = bm.loops.layers.uv.active
        
        # Apply loop attributes (UVs, etc.)
        if uv_layer and loop_data:
            for loop_info in loop_data:
                loop_id = loop_info["id"]
                face_id = loop_info["face"]
                vertex_id = loop_info["vertex"]
                
                face = face_map.get(face_id)
                vertex = vertex_map.get(vertex_id)
                
                if face and vertex:
                    # Find the loop that corresponds to this vertex in this face
                    for loop in face.loops:
                        if loop.vert == vertex:
                            attributes = loop_info.get("attributes", {})
                            if "TEXCOORD_0" in attributes:
                                uv = attributes["TEXCOORD_0"]
                                loop[uv_layer].uv = (uv[0], uv[1])
                            break

        return bm

    def _reconstruct_from_buffer_format(self, bm: BMesh, extension_data: Dict[str, Any]) -> BMesh:
        """Reconstruct BMesh from buffer format data (placeholder for future implementation)."""
        logger.warning("Buffer format reconstruction not yet implemented")
        bm.free()
        return None

    def decode_implicit_triangle_fan(self, triangles: List[Tuple]) -> List[List[int]]:
        """
        Decode triangle fan back to polygon faces.
        
        This provides graceful fallback when EXT_bmesh_encoding is not fully supported.
        """
        if not triangles:
            return []

        faces = []
        current_face_vertices = []
        prev_anchor = None

        for triangle in triangles:
            if len(triangle) < 3:
                continue
                
            anchor = triangle[0]
            
            if anchor != prev_anchor:
                # New face starts
                if current_face_vertices:
                    faces.append(current_face_vertices)
                current_face_vertices = list(triangle)
                prev_anchor = anchor
            else:
                # Continue triangle fan for same face
                # Add the new vertex from this triangle
                new_vertex = triangle[2]  # Third vertex of triangle
                if new_vertex not in current_face_vertices:
                    current_face_vertices.append(new_vertex)

        # Handle last face
        if current_face_vertices:
            faces.append(current_face_vertices)

        return faces

    def apply_bmesh_to_blender_mesh(self, bm: BMesh, mesh: bpy.types.Mesh) -> bool:
        """Apply reconstructed BMesh data to Blender mesh."""
        try:
            # Update the mesh with BMesh data
            bm.to_mesh(mesh)
            mesh.update()
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply BMesh to Blender mesh: {e}")
            return False

    @staticmethod
    def detect_extension_in_primitive(primitive_data: Dict[str, Any]) -> bool:
        """Check if a glTF primitive contains EXT_bmesh_encoding extension."""
        extensions = primitive_data.get("extensions", {})
        return "EXT_bmesh_encoding" in extensions

    @staticmethod
    def extract_extension_data(primitive_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract EXT_bmesh_encoding extension data from glTF primitive."""
        extensions = primitive_data.get("extensions", {})
        return extensions.get("EXT_bmesh_encoding")
