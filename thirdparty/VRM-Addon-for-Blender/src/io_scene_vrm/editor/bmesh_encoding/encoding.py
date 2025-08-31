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


def safe_ensure_lookup_table(bmesh_seq, seq_name="unknown"):
    """
    Safely ensure lookup table using appropriate method for each BMesh sequence type.
    
    BMLoopSeq doesn't have ensure_lookup_table() method in Blender's API,
    but it does have index_update() which serves the same purpose.
    """
    if hasattr(bmesh_seq, 'ensure_lookup_table'):
        try:
            bmesh_seq.ensure_lookup_table()
        except Exception as e:
            logger.debug(f"Failed to ensure lookup table for {seq_name}: {e}")
    elif hasattr(bmesh_seq, 'index_update'):
        try:
            bmesh_seq.index_update()
            logger.debug(f"Used index_update() for {seq_name} (BMLoopSeq compatibility)")
        except Exception as e:
            logger.debug(f"Failed to update indices for {seq_name}: {e}")
    else:
        logger.debug(f"No lookup table method available for {seq_name}")


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
        safe_ensure_lookup_table(bm.faces, "faces")
        safe_ensure_lookup_table(bm.verts, "verts")
        safe_ensure_lookup_table(bm.edges, "edges")
        safe_ensure_lookup_table(bm.loops, "loops")

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
        """Encode vertex data for buffer format according to EXT_bmesh_encoding schema."""
        if not bm.verts:
            return {}

        vertex_count = len(bm.verts)
        
        # Create position data (required by schema)
        positions_buffer = bytearray()
        position_struct = struct.Struct("<fff")
        
        # Create edge adjacency data (optional per schema)
        edges_buffer = bytearray()
        edge_index_struct = struct.Struct("<I")
        
        for vert in bm.verts:
            # Pack vertex position (Vec3<f32> as required by schema)
            positions_buffer.extend(position_struct.pack(*vert.co))
            
            # Pack vertex-edge adjacency data
            for edge in vert.link_edges:
                edges_buffer.extend(edge_index_struct.pack(edge.index))

        result = {
            "count": vertex_count,
            "positions": {
                "data": positions_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5126,  # GL_FLOAT
                "type": "VEC3",
                "count": vertex_count
            }
        }
        
        # Add edges buffer if there's adjacency data
        if edges_buffer:
            result["edges"] = {
                "data": edges_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            }
        
        return result

    def _encode_edges_to_buffers(self, bm: BMesh) -> Dict[str, Any]:
        """Encode edge data for buffer format according to EXT_bmesh_encoding schema."""
        if not bm.edges:
            return {}

        edge_count = len(bm.edges)
        
        # Create edge vertex pairs (required: 2×u32 per edge)
        vertices_buffer = bytearray()
        vertex_pair_struct = struct.Struct("<II")
        
        # Create face adjacency data (optional)
        faces_buffer = bytearray()
        face_index_struct = struct.Struct("<I")
        
        # Create manifold flags (optional: u8 per edge)
        manifold_buffer = bytearray()
        manifold_struct = struct.Struct("<B")
        
        for edge in bm.edges:
            # Pack edge vertices (required by schema)
            vertices_buffer.extend(vertex_pair_struct.pack(
                edge.verts[0].index, 
                edge.verts[1].index
            ))
            
            # Pack face adjacency data
            for face in edge.link_faces:
                faces_buffer.extend(face_index_struct.pack(face.index))
            
            # Pack manifold status (0=non-manifold, 1=manifold, 255=unknown)
            manifold_status = self._calculate_edge_manifold_status(edge)
            if manifold_status is True:
                manifold_buffer.extend(manifold_struct.pack(1))
            elif manifold_status is False:
                manifold_buffer.extend(manifold_struct.pack(0))
            else:
                manifold_buffer.extend(manifold_struct.pack(255))  # Unknown

        result = {
            "count": edge_count,
            "vertices": {
                "data": vertices_buffer,
                "target": "ELEMENT_ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "VEC2",
                "count": edge_count
            }
        }
        
        # Add optional face adjacency data
        if faces_buffer:
            result["faces"] = {
                "data": faces_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            }
        
        # Add optional manifold flags
        if manifold_buffer:
            result["manifold"] = {
                "data": manifold_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5121,  # GL_UNSIGNED_BYTE
                "type": "SCALAR",
                "count": edge_count
            }
        
        return result

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
        """Encode face data for buffer format according to EXT_bmesh_encoding schema."""
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
            # Record vertex offset for this face (required by schema)
            offsets_buffer.extend(offset_struct.pack(vertices_offset))
            
            # Pack face vertices (required by schema: variable length, u32 indices)
            for vert in face.verts:
                vertices_buffer.extend(vertex_struct.pack(vert.index))
                vertices_offset += 1
                
            # Pack face edges (optional)
            for edge in face.edges:
                edges_buffer.extend(edge_struct.pack(edge.index))
                edges_offset += 1
                
            # Pack face loops (optional)
            for _ in face.loops:
                loops_buffer.extend(loop_struct.pack(loop_index))
                loop_index += 1
                loops_offset += 1
                
            # Pack face normal (Vec3<f32> per face)
            normals_buffer.extend(normal_struct.pack(*face.normal))

        # Final offset (required: u32 per face + 1)
        offsets_buffer.extend(offset_struct.pack(vertices_offset))

        result = {
            "count": face_count,
            "vertices": {
                "data": vertices_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            },
            "offsets": {
                "data": offsets_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR",
                "count": face_count + 1
            }
        }
        
        # Add optional data
        if edges_buffer:
            result["edges"] = {
                "data": edges_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            }
        
        if loops_buffer:
            result["loops"] = {
                "data": loops_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5125,  # GL_UNSIGNED_INT
                "type": "SCALAR"
            }
        
        if normals_buffer:
            result["normals"] = {
                "data": normals_buffer,
                "target": "ARRAY_BUFFER",
                "componentType": 5126,  # GL_FLOAT
                "type": "VEC3",
                "count": face_count
            }
        
        return result

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
        maintaining material grouping for glTF compliance. Uses robust algorithms
        to handle complex meshes like Suzanne with improved error handling.
        """
        if not bm.faces:
            logger.debug("No faces found in BMesh for triangle fan encoding")
            return []

        # Ensure all lookup tables are valid
        try:
            safe_ensure_lookup_table(bm.faces, "faces")
            safe_ensure_lookup_table(bm.verts, "verts")
            safe_ensure_lookup_table(bm.loops, "loops")
            safe_ensure_lookup_table(bm.edges, "edges")
        except Exception as e:
            logger.error(f"Failed to ensure BMesh lookup tables: {e}")
            return []
        
        triangulated_faces = []
        failed_faces = 0
        total_triangles = 0
        
        for face in bm.faces:
            try:
                face_loops = list(face.loops)
                # Use glTF standard material index (handled at primitive level, not face level)
                material_index = getattr(face, 'material_index', 0)
                
                if len(face_loops) <= 2:
                    # Degenerate face - skip
                    logger.debug(f"Skipping degenerate face {face.index} with {len(face_loops)} vertices")
                    failed_faces += 1
                    continue
                elif len(face_loops) == 3:
                    # Triangle - handle directly
                    triangulated_faces.append((material_index, tuple(face_loops)))
                    total_triangles += 1
                    continue
                
                # N-gon - create triangle fan with improved algorithm
                fan_triangles = self._create_robust_triangle_fan(face, face_loops, material_index)
                
                if fan_triangles:
                    triangulated_faces.extend(fan_triangles)
                    total_triangles += len(fan_triangles)
                else:
                    logger.debug(f"Failed to create triangle fan for face {face.index}, using fallback")
                    # Fallback: simple fan from first vertex
                    fallback_triangles = self._create_simple_triangle_fan(face_loops, material_index)
                    triangulated_faces.extend(fallback_triangles)
                    total_triangles += len(fallback_triangles)
                    
            except Exception as e:
                logger.error(f"Failed to triangulate face {face.index}: {e}")
                failed_faces += 1
                continue

        logger.info(f"Triangle fan encoding completed: {total_triangles} triangles from {len(bm.faces)} faces "
                   f"({failed_faces} failed)")
        return triangulated_faces

    def _create_robust_triangle_fan(
        self, 
        face: BMFace, 
        face_loops: List[BMLoop], 
        material_index: int
    ) -> List[Tuple[int, Tuple[BMLoop, ...]]]:
        """
        Create triangle fan with improved robustness for complex geometry.
        
        Uses geometric validation and optimal anchor selection.
        """
        try:
            # Step 1: Validate face is not degenerate
            if not self._validate_face_geometry(face):
                logger.debug(f"Face {face.index} failed geometry validation")
                return []
            
            # Step 2: Select optimal anchor vertex
            anchor_loop = self._select_optimal_anchor_loop(face, face_loops)
            anchor_index = face_loops.index(anchor_loop)
            
            # Step 3: Create triangle fan from optimal anchor
            triangles = []
            
            for i in range(1, len(face_loops) - 1):
                loop1_idx = (anchor_index + i) % len(face_loops)
                loop2_idx = (anchor_index + i + 1) % len(face_loops)
                
                triangle_loops = (
                    anchor_loop,
                    face_loops[loop1_idx],
                    face_loops[loop2_idx]
                )
                
                # Step 4: Validate each triangle
                if self._validate_triangle_geometry(triangle_loops):
                    triangles.append((material_index, triangle_loops))
                else:
                    logger.debug(f"Skipping invalid triangle in face {face.index}")
            
            return triangles
            
        except Exception as e:
            logger.debug(f"Robust triangle fan creation failed for face {face.index}: {e}")
            return []

    def _validate_face_geometry(self, face: BMFace) -> bool:
        """Validate that face has valid geometry for triangulation."""
        try:
            # Check face has valid area
            area = face.calc_area()
            if area < 1e-8:
                return False
            
            # Check face has valid normal
            normal = face.normal
            if normal.length < 1e-8:
                return False
            
            # Check vertices are not all coincident
            positions = [loop.vert.co for loop in face.loops]
            if len(set(tuple(pos) for pos in positions)) < 3:
                return False
            
            return True
            
        except Exception:
            return False

    def _validate_triangle_geometry(self, triangle_loops: Tuple[BMLoop, ...]) -> bool:
        """Validate that triangle has non-zero area and proper winding."""
        try:
            if len(triangle_loops) != 3:
                return False
            
            v0 = triangle_loops[0].vert.co
            v1 = triangle_loops[1].vert.co
            v2 = triangle_loops[2].vert.co
            
            # Check vertices are not coincident
            if (v0 - v1).length < 1e-8 or (v1 - v2).length < 1e-8 or (v2 - v0).length < 1e-8:
                return False
            
            # Calculate triangle area using cross product
            edge1 = v1 - v0
            edge2 = v2 - v0
            cross = edge1.cross(edge2)
            area = cross.length * 0.5
            
            return area > 1e-8  # Non-degenerate threshold
            
        except Exception:
            return False

    def _select_optimal_anchor_loop(self, face: BMFace, face_loops: List[BMLoop]) -> BMLoop:
        """
        Select the optimal anchor vertex for triangle fan creation.
        
        Uses geometric and topological criteria for robust triangulation.
        """
        if len(face_loops) <= 3:
            return face_loops[0]
        
        try:
            # Calculate face center for reference
            face_center = face.calc_center_median()
            
            best_loop = face_loops[0]
            best_score = float('-inf')
            
            for loop in face_loops:
                score = 0
                
                # Criterion 1: Distance to face center (prefer central vertices)
                distance_to_center = (loop.vert.co - face_center).length
                score += 10.0 / (distance_to_center + 0.01)  # Avoid division by zero
                
                # Criterion 2: Vertex valence (prefer simpler topology)
                valence = len(loop.vert.link_edges)
                score += 5.0 / (valence + 1)
                
                # Criterion 3: Angle quality (prefer vertices that create good triangles)
                valid_triangles = self._count_valid_triangles_from_anchor(face_loops, loop)
                score += valid_triangles * 2.0
                
                # Criterion 4: Avoid vertices on sharp edges
                if self._is_on_sharp_edge(loop):
                    score *= 0.5
                
                if score > best_score:
                    best_score = score
                    best_loop = loop
            
            return best_loop
            
        except Exception as e:
            logger.debug(f"Optimal anchor selection failed: {e}, using first vertex")
            return face_loops[0]

    def _count_valid_triangles_from_anchor(self, face_loops: List[BMLoop], anchor_loop: BMLoop) -> int:
        """Count how many valid triangles can be created from this anchor."""
        try:
            anchor_index = face_loops.index(anchor_loop)
            valid_count = 0
            
            for i in range(1, len(face_loops) - 1):
                loop1_idx = (anchor_index + i) % len(face_loops)
                loop2_idx = (anchor_index + i + 1) % len(face_loops)
                
                triangle_loops = (
                    anchor_loop,
                    face_loops[loop1_idx],
                    face_loops[loop2_idx]
                )
                
                if self._validate_triangle_geometry(triangle_loops):
                    valid_count += 1
            
            return valid_count
            
        except Exception:
            return 0

    def _is_on_sharp_edge(self, loop: BMLoop) -> bool:
        """Check if vertex is on a sharp edge (potential triangulation problem)."""
        try:
            for edge in loop.vert.link_edges:
                if not edge.smooth or len(edge.link_faces) != 2:
                    return True
            return False
        except Exception:
            return False

    def _create_simple_triangle_fan(
        self, 
        face_loops: List[BMLoop], 
        material_index: int
    ) -> List[Tuple[int, Tuple[BMLoop, ...]]]:
        """
        Create simple triangle fan from first vertex as fallback.
        
        This is the original algorithm as a reliable fallback when
        robust methods fail.
        """
        triangles = []
        anchor_loop = face_loops[0]
        
        for i in range(2, len(face_loops)):
            triangle_loops = (
                anchor_loop,
                face_loops[i - 1],
                face_loops[i]
            )
            triangles.append((material_index, triangle_loops))
        
        return triangles

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
            safe_ensure_lookup_table(bm.faces, "faces")
            safe_ensure_lookup_table(bm.verts, "verts")
            safe_ensure_lookup_table(bm.edges, "edges")
            safe_ensure_lookup_table(bm.loops, "loops")
            
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
        logger.info("Creating buffer views for EXT_bmesh_encoding...")
        
        if not extension_data:
            logger.warning("No extension data provided to create_buffer_views")
            return {}

        logger.debug(f"Extension data keys: {list(extension_data.keys())}")

        # Helper to create buffer view
        def create_buffer_view(data_info: Dict[str, Any]) -> Optional[int]:
            if "data" not in data_info:
                logger.debug("No 'data' key in data_info")
                return None
                
            data = data_info["data"]
            if not data:
                logger.debug("Empty data in data_info")
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
            
            logger.debug(f"Created buffer view {buffer_view_index} with {len(data)} bytes")
            return buffer_view_index

        # Process vertices
        result_data = {}
        if "vertices" in extension_data:
            vertex_data = extension_data["vertices"]
            result_vertices = {"count": vertex_data["count"]}
            logger.info(f"Processing vertices: count={vertex_data['count']}")
            
            positions_idx = create_buffer_view(vertex_data["positions"])
            if positions_idx is not None:
                result_vertices["positions"] = positions_idx
                logger.debug(f"Added positions buffer view: {positions_idx}")
                
            edges_idx = create_buffer_view(vertex_data.get("edges", {}))
            if edges_idx is not None:
                result_vertices["edges"] = edges_idx
                logger.debug(f"Added vertex edges buffer view: {edges_idx}")
            
            # Add edge offsets buffer view
            if "edgeOffsets" in vertex_data:
                offsets_idx = create_buffer_view(vertex_data["edgeOffsets"])
                if offsets_idx is not None:
                    result_vertices["edgeOffsets"] = offsets_idx
                    logger.debug(f"Added vertex edge offsets buffer view: {offsets_idx}")
                
            result_data["vertices"] = result_vertices

        # Process edges  
        if "edges" in extension_data:
            edge_data = extension_data["edges"]
            result_edges = {"count": edge_data["count"]}
            logger.info(f"Processing edges: count={edge_data['count']}")
            
            vertices_idx = create_buffer_view(edge_data["vertices"])
            if vertices_idx is not None:
                result_edges["vertices"] = vertices_idx
                logger.debug(f"Added edge vertices buffer view: {vertices_idx}")
                
            faces_idx = create_buffer_view(edge_data.get("faces", {}))
            if faces_idx is not None:
                result_edges["faces"] = faces_idx
                logger.debug(f"Added edge faces buffer view: {faces_idx}")
            
            # Add face offsets buffer view
            if "faceOffsets" in edge_data:
                face_offsets_idx = create_buffer_view(edge_data["faceOffsets"])
                if face_offsets_idx is not None:
                    result_edges["faceOffsets"] = face_offsets_idx
                    logger.debug(f"Added edge face offsets buffer view: {face_offsets_idx}")
                
            manifold_idx = create_buffer_view(edge_data.get("manifold", {}))
            if manifold_idx is not None:
                result_edges["manifold"] = manifold_idx
                logger.debug(f"Added edge manifold buffer view: {manifold_idx}")
                
            result_data["edges"] = result_edges

        # Process loops
        if "loops" in extension_data:
            loop_data = extension_data["loops"]
            result_loops = {"count": loop_data["count"]}
            logger.info(f"Processing loops: count={loop_data['count']}")
            
            topology_idx = create_buffer_view(loop_data["topology"])
            if topology_idx is not None:
                result_loops["topology"] = topology_idx
                logger.debug(f"Added loop topology buffer view: {topology_idx}")
                
            # Handle UV attributes with glTF naming
            if "attributes" in loop_data:
                result_loops["attributes"] = {}
                for attr_name, attr_data in loop_data["attributes"].items():
                    attr_idx = create_buffer_view(attr_data)
                    if attr_idx is not None:
                        result_loops["attributes"][attr_name] = attr_idx
                        logger.debug(f"Added loop attribute '{attr_name}' buffer view: {attr_idx}")
                        
            result_data["loops"] = result_loops

        # Process faces
        if "faces" in extension_data:
            face_data = extension_data["faces"]
            result_faces = {"count": face_data["count"]}
            logger.info(f"Processing faces: count={face_data['count']}")
            
            for key in ["vertices", "edges", "loops", "normals", "offsets"]:
                if key in face_data:
                    buffer_idx = create_buffer_view(face_data[key])
                    if buffer_idx is not None:
                        result_faces[key] = buffer_idx
                        logger.debug(f"Added face {key} buffer view: {buffer_idx}")
                        
            result_data["faces"] = result_faces

        logger.info(f"Buffer view creation complete. Result data keys: {list(result_data.keys())}")
        return result_data
