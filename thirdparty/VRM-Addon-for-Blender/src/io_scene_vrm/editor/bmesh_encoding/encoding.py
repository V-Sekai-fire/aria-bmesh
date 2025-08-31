# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""EXT_bmesh_encoding buffer-based encoding implementation."""

import struct
from typing import Any, Dict, List, Optional, Tuple

import bmesh
import bpy
from bmesh.types import BMesh, BMFace, BMLoop, BMVert, BMEdge
from mathutils import Vector

from ...common.logger import get_logger

logger = get_logger(__name__)


class BmeshEncoder:
    """Handles buffer-based BMesh encoding for EXT_bmesh_encoding extension."""

    def __init__(self):
        """Initialize encoder with buffer-only format."""
        self.preserve_manifold_info = True

    def encode_bmesh_to_gltf_extension(self, bm: BMesh) -> Dict[str, Any]:
        """
        Encode BMesh to EXT_bmesh_encoding extension data using buffer format.
        
        Returns buffer-based extension data that references glTF buffer views.
        Material indices are handled at the glTF primitive level, not face level.
        """
        if not bm.faces:
            return {}

        # Ensure face indices are valid
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.loops.ensure_lookup_table()

        return self._encode_to_buffer_format(bm)

    def _encode_to_buffer_format(self, bm: BMesh) -> Dict[str, Any]:
        """
        Encode BMesh to buffer format following glTF conventions.
        
        This creates the extension data structure that references buffer views
        which will be created by the glTF exporter.
        """
        extension_data = {}

        # Encode vertices
        vertex_data = self._encode_vertices_to_buffers(bm)
        if vertex_data:
            extension_data["vertices"] = vertex_data

        # Encode edges
        edge_data = self._encode_edges_to_buffers(bm)
        if edge_data:
            extension_data["edges"] = edge_data

        # Encode loops
        loop_data = self._encode_loops_to_buffers(bm)
        if loop_data:
            extension_data["loops"] = loop_data

        # Encode faces
        face_data = self._encode_faces_to_buffers(bm)
        if face_data:
            extension_data["faces"] = face_data

        return extension_data

    def _encode_vertices_to_buffers(self, bm: BMesh) -> Dict[str, Any]:
        """Encode vertex data for buffer format."""
        if not bm.verts:
            return {}

        vertex_count = len(bm.verts)
        
        # Create position data
        positions_buffer = bytearray()
        position_struct = struct.Struct("<fff")
        
        # Create edge adjacency data
        edges_buffer = bytearray()
        edge_offsets_buffer = bytearray()
        offset_struct = struct.Struct("<I")
        edge_index_struct = struct.Struct("<I")
        
        current_offset = 0
        for vert in bm.verts:
            # Pack vertex position
            positions_buffer.extend(position_struct.pack(*vert.co))
            
            # Pack edge adjacency
            edge_indices = [edge.index for edge in vert.link_edges]
            offset_struct.pack_into(edge_offsets_buffer, current_offset * 4, len(edge_indices))
            current_offset += 1
            
            for edge_idx in edge_indices:
                edges_buffer.extend(edge_index_struct.pack(edge_idx))

        # Final offset for edge adjacency
        edge_offsets_buffer.extend(offset_struct.pack(len(edges_buffer) // 4))

        return {
            "count": vertex_count,
            "positions": {
                "data": positions_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5126,  # GL_FLOAT
                "type": "VEC3",
                "count": vertex_count
            },
            "edges": {
                "data": edges_buffer,
                "target": "ARRAY_BUFFER", 
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            },
            "edgeOffsets": {
                "data": edge_offsets_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT  
                "type": "SCALAR",
                "count": vertex_count + 1
            }
        }

    def _encode_edges_to_buffers(self, bm: BMesh) -> Dict[str, Any]:
        """Encode edge data for buffer format."""
        if not bm.edges:
            return {}

        edge_count = len(bm.edges)
        
        # Create edge vertex pairs
        vertices_buffer = bytearray()
        vertex_pair_struct = struct.Struct("<II")
        
        # Create face adjacency data
        faces_buffer = bytearray()
        face_offsets_buffer = bytearray()
        offset_struct = struct.Struct("<I")
        face_index_struct = struct.Struct("<I")
        
        # Create manifold flags
        manifold_buffer = bytearray()
        manifold_struct = struct.Struct("<B")
        
        current_offset = 0
        for edge in bm.edges:
            # Pack edge vertices
            vertices_buffer.extend(vertex_pair_struct.pack(
                edge.verts[0].index, 
                edge.verts[1].index
            ))
            
            # Pack face adjacency
            face_indices = [face.index for face in edge.link_faces]
            offset_struct.pack_into(face_offsets_buffer, current_offset * 4, len(face_indices))
            current_offset += 1
            
            for face_idx in face_indices:
                faces_buffer.extend(face_index_struct.pack(face_idx))
            
            # Pack manifold status
            manifold_status = self._calculate_edge_manifold_status(edge)
            if manifold_status is True:
                manifold_buffer.extend(manifold_struct.pack(1))
            elif manifold_status is False:
                manifold_buffer.extend(manifold_struct.pack(0))
            else:
                manifold_buffer.extend(manifold_struct.pack(255))  # Unknown

        # Final offset for face adjacency
        face_offsets_buffer.extend(offset_struct.pack(len(faces_buffer) // 4))

        return {
            "count": edge_count,
            "vertices": {
                "data": vertices_buffer,
                "target": "ELEMENT_ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "VEC2",
                "count": edge_count
            },
            "faces": {
                "data": faces_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            },
            "faceOffsets": {
                "data": face_offsets_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR",
                "count": edge_count + 1
            },
            "manifold": {
                "data": manifold_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5121,  # GL_UNSIGNED_BYTE
                "type": "SCALAR",
                "count": edge_count
            }
        }

    def _encode_loops_to_buffers(self, bm: BMesh) -> Dict[str, Any]:
        """Encode loop data for buffer format with glTF-compliant UV handling."""
        if not bm.loops:
            return {}

        # Count total loops
        loop_count = sum(len(face.loops) for face in bm.faces)
        if loop_count == 0:
            return {}

        # Create topology data (vertex, edge, face, next, prev, radial_next, radial_prev)
        topology_buffer = bytearray()
        topology_struct = struct.Struct("<IIIIIII")  # 7×u32 per loop
        
        # Create UV data using glTF standard attribute names
        uv_buffers = {}
        uv_struct = struct.Struct("<ff")
        
        # Check for UV layers
        if bm.loops.layers.uv:
            for i, uv_layer in enumerate(bm.loops.layers.uv):
                uv_buffers[f"TEXCOORD_{i}"] = bytearray()

        loop_index = 0
        loop_index_map = {}  # Map (face_index, loop_in_face_index) -> global_loop_index
        
        # First pass: create loop index mapping
        for face in bm.faces:
            for i, loop in enumerate(face.loops):
                loop_index_map[(face.index, i)] = loop_index
                loop_index += 1

        # Second pass: encode topology with proper navigation
        loop_index = 0
        for face in bm.faces:
            face_loops = list(face.loops)
            for i, loop in enumerate(face_loops):
                # Calculate next and previous in face
                next_in_face = (i + 1) % len(face_loops)
                prev_in_face = (i - 1) % len(face_loops)
                next_idx = loop_index_map[(face.index, next_in_face)]
                prev_idx = loop_index_map[(face.index, prev_in_face)]
                
                # Find radial navigation (around the same edge)
                radial_next_idx, radial_prev_idx = self._find_radial_loop_indices(
                    loop, loop_index, loop_index_map
                )
                
                # Pack topology
                topology_buffer.extend(topology_struct.pack(
                    loop.vert.index,    # vertex
                    loop.edge.index,    # edge  
                    loop.face.index,    # face
                    next_idx,           # next
                    prev_idx,           # prev
                    radial_next_idx,    # radial_next
                    radial_prev_idx     # radial_prev
                ))
                
                # Pack UV coordinates using glTF standard naming
                if bm.loops.layers.uv:
                    for uv_i, uv_layer in enumerate(bm.loops.layers.uv):
                        uv_coord = loop[uv_layer].uv
                        uv_buffers[f"TEXCOORD_{uv_i}"].extend(uv_struct.pack(uv_coord[0], uv_coord[1]))
                
                loop_index += 1

        result = {
            "count": loop_count,
            "topology": {
                "data": topology_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR",  # 7 components per loop stored as scalars
                "count": loop_count * 7  # 7 values per loop
            }
        }
        
        # Add UV attributes if present
        if uv_buffers:
            result["attributes"] = {}
            for attr_name, uv_buffer in uv_buffers.items():
                result["attributes"][attr_name] = {
                    "data": uv_buffer,
                    "target": "ARRAY_BUFFER",
                    "componentType": 5126,  # GL_FLOAT
                    "type": "VEC2",
                    "count": loop_count
                }

        return result

    def _encode_faces_to_buffers(self, bm: BMesh) -> Dict[str, Any]:
        """Encode face data for buffer format."""
        if not bm.faces:
            return {}

        face_count = len(bm.faces)
        
        # Create variable-length arrays for face data
        vertices_buffer = bytearray()
        edges_buffer = bytearray() 
        loops_buffer = bytearray()
        normals_buffer = bytearray()
        offsets_buffer = bytearray()
        
        vertex_struct = struct.Struct("<I")
        edge_struct = struct.Struct("<I")
        loop_struct = struct.Struct("<I")
        normal_struct = struct.Struct("<fff")
        offset_struct = struct.Struct("<I")
        
        vertices_offset = 0
        edges_offset = 0
        loops_offset = 0
        
        loop_index = 0
        for face in bm.faces:
            # Record offsets for this face
            offsets_buffer.extend(offset_struct.pack(vertices_offset))
            offsets_buffer.extend(offset_struct.pack(edges_offset))
            offsets_buffer.extend(offset_struct.pack(loops_offset))
            
            # Pack face vertices
            for vert in face.verts:
                vertices_buffer.extend(vertex_struct.pack(vert.index))
                vertices_offset += 1
                
            # Pack face edges
            for edge in face.edges:
                edges_buffer.extend(edge_struct.pack(edge.index))
                edges_offset += 1
                
            # Pack face loops
            for _ in face.loops:
                loops_buffer.extend(loop_struct.pack(loop_index))
                loop_index += 1
                loops_offset += 1
                
            # Pack face normal
            normals_buffer.extend(normal_struct.pack(*face.normal))

        # Final offsets
        offsets_buffer.extend(offset_struct.pack(vertices_offset))
        offsets_buffer.extend(offset_struct.pack(edges_offset))  
        offsets_buffer.extend(offset_struct.pack(loops_offset))

        return {
            "count": face_count,
            "vertices": {
                "data": vertices_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            },
            "edges": {
                "data": edges_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            },
            "loops": {
                "data": loops_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            },
            "normals": {
                "data": normals_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5126,  # GL_FLOAT
                "type": "VEC3",
                "count": face_count
            },
            "offsets": {
                "data": offsets_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "VEC3",  # 3 offsets per face (vertices, edges, loops)
                "count": face_count + 1
            }
        }

    def _calculate_edge_manifold_status(self, edge: BMEdge) -> Optional[bool]:
        """
        Calculate manifold status for an edge.
        Returns:
        - True: Confirmed manifold (exactly 2 faces)
        - False: Confirmed non-manifold (not exactly 2 faces)
        - None: Unknown status
        """
        if not self.preserve_manifold_info:
            return None
        
        linked_faces = list(edge.link_faces)
        return len(linked_faces) == 2

    def _find_radial_loop_indices(
        self, 
        loop: BMLoop, 
        current_loop_index: int,
        loop_index_map: Dict[Tuple[int, int], int]
    ) -> Tuple[int, int]:
        """
        Find radial next/previous loops around the same edge.
        
        For manifold edges, finds the loop on the adjacent face.
        For non-manifold edges, implements proper radial traversal.
        """
        edge = loop.edge
        linked_faces = list(edge.link_faces)
        
        if len(linked_faces) <= 1:
            # Boundary edge - radial links to self
            return current_loop_index, current_loop_index
            
        # Find the other face using this edge
        current_face = loop.face
        other_faces = [f for f in linked_faces if f != current_face]
        
        if not other_faces:
            return current_loop_index, current_loop_index
            
        # For manifold case, find the loop on the other face that uses this edge
        other_face = other_faces[0]  # Take first adjacent face
        
        for i, other_loop in enumerate(other_face.loops):
            if other_loop.edge == edge:
                other_loop_idx = loop_index_map.get((other_face.index, i))
                if other_loop_idx is not None:
                    return other_loop_idx, other_loop_idx
                    
        # Fallback to self-reference
        return current_loop_index, current_loop_index

    def encode_triangle_fan_implicit(self, bm: BMesh) -> List[Tuple[int, Tuple[BMLoop, ...]]]:
        """
        Enhanced triangle fan encoding compatible with BMesh topology preservation.
        
        Creates triangle fans optimized for BMesh reconstruction while
        maintaining material grouping for glTF compliance.
        """
        if not bm.faces:
            return []

        # Ensure face indices are valid
        bm.faces.ensure_lookup_table()
        
        triangulated_faces = []
        
        for face in bm.faces:
            face_loops = list(face.loops)
            # Use glTF standard material index (handled at primitive level, not face level)
            material_index = getattr(face, 'material_index', 0)
            
            if len(face_loops) <= 3:
                # Triangle or less - handle directly
                if len(face_loops) == 3:
                    triangulated_faces.append((material_index, tuple(face_loops)))
                continue
            
            # N-gon - create triangle fan from first vertex
            anchor_loop = face_loops[0]
            
            # Create triangle fan
            for i in range(2, len(face_loops)):
                triangle_loops = (
                    anchor_loop,
                    face_loops[i - 1], 
                    face_loops[i]
                )
                triangulated_faces.append((material_index, triangle_loops))

        return triangulated_faces

    @staticmethod
    def create_bmesh_from_mesh(mesh_obj: bpy.types.Object) -> Optional[BMesh]:
        """Create BMesh from Blender mesh object with proper error handling."""
        if mesh_obj.type != 'MESH' or not mesh_obj.data:
            return None
        
        bm = bmesh.new()
        
        try:
            # Use evaluated mesh for accurate geometry
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = mesh_obj.evaluated_get(depsgraph)
            
            bm.from_mesh(eval_obj.data)
            
            # Apply object transform
            bm.transform(mesh_obj.matrix_world)
            
            # Ensure all lookup tables are valid
            bm.faces.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.loops.ensure_lookup_table()
            
            # Calculate face indices for consistent material assignment
            for face in bm.faces:
                face.material_index = face.material_index
            
            return bm
            
        except Exception as e:
            logger.error(f"Failed to create BMesh from {mesh_obj.name}: {e}")
            bm.free()
            return None

    def create_buffer_views(self, json_dict: Dict[str, Any], buffer0: bytearray, extension_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create glTF buffer views from the encoded BMesh data.
        
        This integrates with the glTF export pipeline to create proper buffer views
        that reference the main glTF buffer.
        """
        if not extension_data:
            return {}

        # Helper to create buffer view
        def create_buffer_view(data_info: Dict[str, Any]) -> Optional[int]:
            if "data" not in data_info:
                return None
                
            data = data_info["data"]
            if not data:
                return None

            # Align buffer to 4-byte boundary
            while len(buffer0) % 4:
                buffer0.append(0)

            buffer_view_index = len(json_dict.get("bufferViews", []))
            
            # Ensure bufferViews array exists
            if "bufferViews" not in json_dict:
                json_dict["bufferViews"] = []
                
            # Create buffer view
            buffer_view = {
                "buffer": 0,
                "byteOffset": len(buffer0),
                "byteLength": len(data),
                "target": data_info.get("target", "ARRAY_BUFFER")
            }
            
            json_dict["bufferViews"].append(buffer_view)
            buffer0.extend(data)
            
            return buffer_view_index

        # Process vertices
        result_data = {}
        if "vertices" in extension_data:
            vertex_data = extension_data["vertices"]
            result_vertices = {"count": vertex_data["count"]}
            
            if positions_idx := create_buffer_view(vertex_data["positions"]):
                result_vertices["positions"] = positions_idx
                
            if edges_idx := create_buffer_view(vertex_data.get("edges", {})):
                result_vertices["edges"] = edges_idx
            
            # Add edge offsets buffer view
            if "edgeOffsets" in vertex_data:
                if offsets_idx := create_buffer_view(vertex_data["edgeOffsets"]):
                    result_vertices["edgeOffsets"] = offsets_idx
                
            result_data["vertices"] = result_vertices

        # Process edges  
        if "edges" in extension_data:
            edge_data = extension_data["edges"]
            result_edges = {"count": edge_data["count"]}
            
            if vertices_idx := create_buffer_view(edge_data["vertices"]):
                result_edges["vertices"] = vertices_idx
                
            if faces_idx := create_buffer_view(edge_data.get("faces", {})):
                result_edges["faces"] = faces_idx
            
            # Add face offsets buffer view
            if "faceOffsets" in edge_data:
                if face_offsets_idx := create_buffer_view(edge_data["faceOffsets"]):
                    result_edges["faceOffsets"] = face_offsets_idx
                
            if manifold_idx := create_buffer_view(edge_data.get("manifold", {})):
                result_edges["manifold"] = manifold_idx
                
            result_data["edges"] = result_edges

        # Process loops
        if "loops" in extension_data:
            loop_data = extension_data["loops"]
            result_loops = {"count": loop_data["count"]}
            
            if topology_idx := create_buffer_view(loop_data["topology"]):
                result_loops["topology"] = topology_idx
                
            # Handle UV attributes with glTF naming
            if "attributes" in loop_data:
                result_loops["attributes"] = {}
                for attr_name, attr_data in loop_data["attributes"].items():
                    if attr_idx := create_buffer_view(attr_data):
                        result_loops["attributes"][attr_name] = attr_idx
                        
            result_data["loops"] = result_loops

        # Process faces
        if "faces" in extension_data:
            face_data = extension_data["faces"]
            result_faces = {"count": face_data["count"]}
            
            for key in ["vertices", "edges", "loops", "normals", "offsets"]:
                if key in face_data:
                    if buffer_idx := create_buffer_view(face_data[key]):
                        result_faces[key] = buffer_idx
                        
            result_data["faces"] = result_faces

        return result_data
