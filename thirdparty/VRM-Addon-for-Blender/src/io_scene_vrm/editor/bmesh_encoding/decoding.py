# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""EXT_bmesh_encoding import and decoding algorithms."""

import struct
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
        
        Only supports buffer-based reconstruction as per updated specification.
        """
        if not extension_data:
            return None

        try:
            # Check if we have explicit BMesh topology data
            if self._has_explicit_topology_data(extension_data):
                return self._reconstruct_from_buffer_format(extension_data)
            else:
                # Fallback to standard glTF import
                logger.info("EXT_bmesh_encoding: No topology data found, using fallback")
                return None  # Let standard glTF import handle it
                
        except Exception as e:
            logger.error(f"Failed to decode EXT_bmesh_encoding: {e}")
            return None

    def _has_explicit_topology_data(self, extension_data: Dict[str, Any]) -> bool:
        """Check if extension data contains explicit BMesh topology."""
        required_keys = ["vertices", "edges", "loops", "faces"]
        return all(key in extension_data for key in required_keys)

    def _reconstruct_from_buffer_format(self, extension_data: Dict[str, Any]) -> Optional[BMesh]:
        """Reconstruct BMesh from buffer format data."""
        bm = bmesh.new()
        
        try:
            vertex_data = extension_data.get("vertices", {})
            edge_data = extension_data.get("edges", {})
            loop_data = extension_data.get("loops", {})
            face_data = extension_data.get("faces", {})

            # Ensure all components have buffer format structure
            if not (isinstance(vertex_data, dict) and "count" in vertex_data):
                logger.warning("EXT_bmesh_encoding: Invalid vertex data format")
                bm.free()
                return None

            # Get the glTF context to read buffer views
            gltf_data = getattr(bpy.context, '_gltf_import_data', None)
            if not gltf_data:
                logger.error("No glTF import data available for buffer reconstruction")
                bm.free()
                return None

            # Reconstruct vertices
            vertex_map = {}
            if vertex_data and vertex_data.get("count", 0) > 0:
                vertex_map = self._reconstruct_vertices_from_buffers(
                    bm, vertex_data, gltf_data
                )

            if not vertex_map:
                logger.warning("No vertices reconstructed from buffer data")
                bm.free()
                return None

            # Reconstruct edges
            edge_map = {}
            if edge_data and edge_data.get("count", 0) > 0:
                edge_map = self._reconstruct_edges_from_buffers(
                    bm, edge_data, vertex_map, gltf_data
                )

            # Reconstruct faces (needed before loops for face references)
            face_map = {}
            if face_data and face_data.get("count", 0) > 0:
                face_map = self._reconstruct_faces_from_buffers(
                    bm, face_data, vertex_map, edge_map, gltf_data
                )

            # Apply loop data (UV coordinates, etc.)
            if loop_data and loop_data.get("count", 0) > 0:
                self._apply_loop_data_from_buffers(
                    bm, loop_data, vertex_map, edge_map, face_map, gltf_data
                )

            # Ensure all lookup tables are valid
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.loops.ensure_lookup_table()

            return bm

        except Exception as e:
            logger.error(f"Failed to reconstruct BMesh from buffer format: {e}")
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

    def _read_buffer_view(self, gltf_data: Any, buffer_view_index: int, component_type: int, count: int, type_name: str) -> Optional[Any]:
        """Read data from a glTF buffer view."""
        try:
            buffer_views = getattr(gltf_data, 'buffer_views', None) or getattr(gltf_data, 'bufferViews', [])
            if not buffer_views or buffer_view_index >= len(buffer_views):
                return None
                
            buffer_view = buffer_views[buffer_view_index]
            buffers = getattr(gltf_data, 'buffers', [])
            
            if not buffers or buffer_view.get('buffer', 0) >= len(buffers):
                return None
                
            buffer_data = buffers[buffer_view.get('buffer', 0)]
            byte_offset = buffer_view.get('byteOffset', 0)
            byte_length = buffer_view.get('byteLength', 0)
            
            if isinstance(buffer_data, bytes):
                data = buffer_data[byte_offset:byte_offset + byte_length]
            elif hasattr(buffer_data, 'data'):
                data = buffer_data.data[byte_offset:byte_offset + byte_length]
            else:
                logger.warning(f"Unsupported buffer data type: {type(buffer_data)}")
                return None

            # Parse based on component type and format
            if component_type == 5126:  # GL_FLOAT
                if type_name == "VEC3":
                    return struct.unpack(f"<{count * 3}f", data)
                elif type_name == "VEC2": 
                    return struct.unpack(f"<{count * 2}f", data)
                else:  # SCALAR
                    return struct.unpack(f"<{count}f", data)
            elif component_type == 5125:  # GL_UNSIGNED_INT
                return struct.unpack(f"<{count}I", data)
            elif component_type == 5121:  # GL_UNSIGNED_BYTE
                return struct.unpack(f"<{count}B", data)
            else:
                logger.warning(f"Unsupported component type: {component_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read buffer view {buffer_view_index}: {e}")
            return None

    def _reconstruct_vertices_from_buffers(self, bm: BMesh, vertex_data: Dict[str, Any], gltf_data: Any) -> Dict[int, BMVert]:
        """Reconstruct vertices from buffer data."""
        vertex_map = {}
        vertex_count = vertex_data.get("count", 0)
        
        if vertex_count == 0:
            return vertex_map

        # Read position data
        positions_buffer_index = vertex_data.get("positions")
        if positions_buffer_index is None:
            return vertex_map

        positions = self._read_buffer_view(gltf_data, positions_buffer_index, 5126, vertex_count, "VEC3")
        if not positions:
            return vertex_map

        # Create vertices
        for i in range(vertex_count):
            pos_idx = i * 3
            position = (positions[pos_idx], positions[pos_idx + 1], positions[pos_idx + 2])
            vert = bm.verts.new(position)
            vertex_map[i] = vert

        return vertex_map

    def _reconstruct_edges_from_buffers(self, bm: BMesh, edge_data: Dict[str, Any], vertex_map: Dict[int, BMVert], gltf_data: Any) -> Dict[int, BMEdge]:
        """Reconstruct edges from buffer data."""
        edge_map = {}
        edge_count = edge_data.get("count", 0)
        
        if edge_count == 0:
            return edge_map

        # Read edge vertex pairs
        vertices_buffer_index = edge_data.get("vertices")
        if vertices_buffer_index is None:
            return edge_map

        edge_vertices = self._read_buffer_view(gltf_data, vertices_buffer_index, 5125, edge_count * 2, "VEC2")
        if not edge_vertices:
            return edge_map

        # Create edges
        for i in range(edge_count):
            vert_idx1 = edge_vertices[i * 2]
            vert_idx2 = edge_vertices[i * 2 + 1]
            
            vert1 = vertex_map.get(vert_idx1)
            vert2 = vertex_map.get(vert_idx2)
            
            if vert1 and vert2:
                try:
                    edge = bm.edges.new([vert1, vert2])
                    edge_map[i] = edge
                except ValueError:
                    # Edge already exists, find it
                    for existing_edge in bm.edges:
                        if set(existing_edge.verts) == {vert1, vert2}:
                            edge_map[i] = existing_edge
                            break

        return edge_map

    def _reconstruct_faces_from_buffers(self, bm: BMesh, face_data: Dict[str, Any], vertex_map: Dict[int, BMVert], edge_map: Dict[int, BMEdge], gltf_data: Any) -> Dict[int, BMFace]:
        """Reconstruct faces from buffer data."""
        face_map = {}
        face_count = face_data.get("count", 0)
        
        if face_count == 0:
            return face_map

        # Read face vertex data and offsets
        vertices_buffer_index = face_data.get("vertices")
        offsets_buffer_index = face_data.get("offsets")
        
        if vertices_buffer_index is None or offsets_buffer_index is None:
            return face_map

        # Read offsets to know how to parse variable-length arrays
        offsets = self._read_buffer_view(gltf_data, offsets_buffer_index, 5125, (face_count + 1) * 3, "VEC3")
        if not offsets:
            return face_map

        # Calculate total vertex indices needed
        max_vertex_offset = offsets[(face_count) * 3]  # Final offset
        face_vertices_data = self._read_buffer_view(gltf_data, vertices_buffer_index, 5125, max_vertex_offset, "SCALAR")
        
        if not face_vertices_data:
            return face_map

        # Create faces
        for i in range(face_count):
            vertex_start = offsets[i * 3]
            vertex_end = offsets[(i + 1) * 3] if i + 1 < face_count else offsets[face_count * 3]
            
            # Get vertex indices for this face
            face_vertex_indices = face_vertices_data[vertex_start:vertex_end]
            
            # Convert to BMVert objects
            face_verts = []
            for vert_idx in face_vertex_indices:
                vert = vertex_map.get(vert_idx)
                if vert:
                    face_verts.append(vert)
                    
            if len(face_verts) >= 3:
                try:
                    face = bm.faces.new(face_verts)
                    face_map[i] = face
                except ValueError as e:
                    logger.warning(f"Failed to create face {i}: {e}")

        return face_map

    def _apply_loop_data_from_buffers(self, bm: BMesh, loop_data: Dict[str, Any], vertex_map: Dict[int, BMVert], edge_map: Dict[int, BMEdge], face_map: Dict[int, BMFace], gltf_data: Any) -> None:
        """Apply loop data (UV coordinates, etc.) from buffer data."""
        loop_count = loop_data.get("count", 0)
        if loop_count == 0:
            return

        # Read UV attributes if present
        attributes = loop_data.get("attributes", {})
        uv_data = {}
        
        for attr_name, buffer_index in attributes.items():
            if attr_name.startswith("TEXCOORD_"):
                uv_coords = self._read_buffer_view(gltf_data, buffer_index, 5126, loop_count, "VEC2")
                if uv_coords:
                    uv_data[attr_name] = uv_coords

        # Apply UV data to loops
        if uv_data:
            # Ensure UV layer exists
            if not bm.loops.layers.uv:
                bm.loops.layers.uv.new()
            
            uv_layer = bm.loops.layers.uv.active
            if uv_layer:
                loop_index = 0
                for face in bm.faces:
                    for loop in face.loops:
                        if loop_index < loop_count and "TEXCOORD_0" in uv_data:
                            uv_coords = uv_data["TEXCOORD_0"]
                            uv_idx = loop_index * 2
                            if uv_idx + 1 < len(uv_coords):
                                loop[uv_layer].uv = (uv_coords[uv_idx], uv_coords[uv_idx + 1])
                        loop_index += 1
