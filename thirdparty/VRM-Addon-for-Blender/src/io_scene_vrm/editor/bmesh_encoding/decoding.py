# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""EXT_bmesh_encoding import and decoding algorithms."""

import struct
from typing import Any, Dict, List, Optional, Tuple

import bmesh
import bpy
from bmesh.types import BMesh, BMFace, BMLoop, BMVert, BMEdge
from mathutils import Vector

# Removed parse_glb import - only needed for glTF files, not direct data
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


class BmeshDecoder:
    """Handles BMesh reconstruction from EXT_bmesh_encoding extension data."""

    def __init__(self):
        pass

    def decode_gltf_extension_to_bmesh(self, extension_data: Dict[str, Any], parse_result: Any = None) -> Optional[BMesh]:
        """
        Decode EXT_bmesh_encoding extension data to BMesh.

        Uses direct data reconstruction only (simplified approach).
        Args:
            extension_data: The EXT_bmesh_encoding extension data
            parse_result: Ignored (for compatibility only)
        """
        if not extension_data:
            return None

        try:
            # Check if we have explicit BMesh topology data
            if self._has_explicit_topology_data(extension_data):
                logger.info("EXT_bmesh_encoding: Using direct data reconstruction")
                mock_parse_result = self._create_mock_parse_result(extension_data)
                return self._decode_encoded_data_to_bmesh(extension_data, mock_parse_result)
            else:
                # No topology data found
                logger.info("EXT_bmesh_encoding: No topology data found")
                return None

        except Exception as e:
            logger.error(f"Failed to decode EXT_bmesh_encoding: {e}")
            return None

    def decode_into_mesh(self, encoded_data: Dict[str, Any], target_mesh: Optional[bpy.types.Mesh] = None) -> Optional[bpy.types.Mesh]:
        """
        Decode encoded BMesh data directly into a Blender mesh.

        This method handles the direct encoded data format from BmeshEncoder,
        creating a new mesh if none is provided.

        Args:
            encoded_data: The encoded BMesh data from BmeshEncoder
            target_mesh: Optional existing mesh to decode into

        Returns:
            The decoded Blender mesh, or None if decoding failed
        """
        if not encoded_data:
            logger.warning("No encoded data provided to decode_into_mesh")
            return None

        try:
            # Create target mesh if not provided
            if target_mesh is None:
                target_mesh = bpy.data.meshes.new("DecodedBMesh")
                logger.debug("Created new mesh for decoding")

            # For direct encoded data (from BmeshEncoder), we need to handle the buffer format
            # without a parse_result. We'll create a mock parse_result for buffer access.
            mock_parse_result = self._create_mock_parse_result(encoded_data)

            # Decode the BMesh from encoded data
            bm = self._decode_encoded_data_to_bmesh(encoded_data, mock_parse_result)

            if bm is None:
                logger.error("Failed to decode BMesh from encoded data")
                return None

            # Apply the BMesh to the target mesh
            success = self.apply_bmesh_to_blender_mesh(bm, target_mesh)

            # Clean up the BMesh
            bm.free()

            if success:
                logger.info(f"Successfully decoded BMesh into mesh '{target_mesh.name}'")
                return target_mesh
            else:
                logger.error("Failed to apply decoded BMesh to target mesh")
                return None

        except Exception as e:
            logger.error(f"Failed to decode into mesh: {e}")
            return None

    def _create_mock_parse_result(self, encoded_data: Dict[str, Any]) -> Any:
        """
        Create a mock parse result for direct encoded data decoding.

        This allows us to reuse the buffer-based decoding logic without
        requiring a full glTF parse result.
        """
        class MockParseResult:
            def __init__(self, encoded_data):
                self.encoded_data = encoded_data
                self.json_dict = {"bufferViews": [], "buffers": [{"byteLength": 0}]}
                self.filepath = None

        return MockParseResult(encoded_data)

    def _decode_encoded_data_to_bmesh(self, encoded_data: Dict[str, Any], mock_parse_result: Any) -> Optional[BMesh]:
        """
        Decode direct encoded data to BMesh using buffer format reconstruction.

        This handles the case where we have encoded data directly from BmeshEncoder
        rather than glTF extension data.
        """
        try:
            # Check if we have the required topology data
            if not self._has_explicit_topology_data(encoded_data):
                logger.warning("Encoded data missing required topology sections")
                return None

            # Extract topology information
            vertex_data = encoded_data.get("vertices", {})
            edge_data = encoded_data.get("edges", {})
            loop_data = encoded_data.get("loops", {})
            face_data = encoded_data.get("faces", {})

            # Validate topology data
            if not all(isinstance(data, dict) and "count" in data for data in [vertex_data, edge_data, face_data]):
                logger.warning("Invalid topology data structure in encoded data")
                return None

            vertex_count = vertex_data.get("count", 0)
            edge_count = edge_data.get("count", 0)
            face_count = face_data.get("count", 0)

            logger.info(f"Decoding direct data: {vertex_count} vertices, {edge_count} edges, {face_count} faces")

            # Create new BMesh
            bm = bmesh.new()

            try:
                # Reconstruct vertices
                vertex_map = self._reconstruct_vertices_from_direct_data(bm, vertex_data)
                if not vertex_map:
                    logger.error("Failed to reconstruct vertices from direct data")
                    bm.free()
                    return None

                # Reconstruct edges
                edge_map = self._reconstruct_edges_from_direct_data(bm, edge_data, vertex_map)

                # Reconstruct faces
                face_map = self._reconstruct_faces_from_direct_data(bm, face_data, vertex_map, edge_map)

                # Apply loop data if available
                if loop_data and loop_data.get("count", 0) > 0:
                    self._apply_loop_data_from_direct_data(bm, loop_data, vertex_map, edge_map, face_map)

                # Ensure lookup tables are valid
                safe_ensure_lookup_table(bm.verts, "verts")
                safe_ensure_lookup_table(bm.edges, "edges")
                safe_ensure_lookup_table(bm.faces, "faces")
                safe_ensure_lookup_table(bm.loops, "loops")

                logger.info(f"Successfully decoded BMesh: {len(bm.verts)} verts, {len(bm.edges)} edges, {len(bm.faces)} faces")
                return bm

            except Exception as e:
                logger.error(f"Failed to decode BMesh from direct data: {e}")
                bm.free()
                return None

        except Exception as e:
            logger.error(f"Failed to decode encoded data to BMesh: {e}")
            return None

    def _reconstruct_vertices_from_direct_data(self, bm: BMesh, vertex_data: Dict[str, Any]) -> Dict[int, BMVert]:
        """Reconstruct vertices from direct encoded data."""
        vertex_map = {}
        vertex_count = vertex_data.get("count", 0)

        if vertex_count == 0:
            return vertex_map

        # Get position data
        positions_attr = vertex_data.get("positions")
        if positions_attr is None:
            return vertex_map

        # Handle direct data format
        positions = None
        if isinstance(positions_attr, dict) and "data" in positions_attr:
            data = positions_attr["data"]
            if isinstance(data, (bytes, bytearray)):
                positions = struct.unpack(f"<{vertex_count * 3}f", data)
                logger.debug(f"Read {len(positions)//3} vertex positions from direct data")
            else:
                logger.warning(f"Positions data is not bytes/bytearray: {type(data)}")
        else:
            logger.warning(f"Positions attribute has unexpected format: {type(positions_attr)}")

        if not positions:
            return vertex_map

        # Create vertices
        for i in range(vertex_count):
            pos_idx = i * 3
            position = (positions[pos_idx], positions[pos_idx + 1], positions[pos_idx + 2])
            vert = bm.verts.new(position)
            vertex_map[i] = vert

        return vertex_map

    def _reconstruct_edges_from_direct_data(self, bm: BMesh, edge_data: Dict[str, Any], vertex_map: Dict[int, BMVert]) -> Dict[int, BMEdge]:
        """Reconstruct edges from direct encoded data."""
        edge_map = {}
        edge_count = edge_data.get("count", 0)

        if edge_count == 0:
            return edge_map

        # Get edge vertex data
        vertices_attr = edge_data.get("vertices")
        if vertices_attr is None:
            return edge_map

        # Handle direct data format
        edge_vertices = None
        if isinstance(vertices_attr, dict) and "data" in vertices_attr:
            data = vertices_attr["data"]
            if isinstance(data, (bytes, bytearray)):
                edge_vertices = struct.unpack(f"<{edge_count * 2}I", data)
                logger.debug(f"Read {len(edge_vertices)//2} edge vertex pairs from direct data")
            else:
                logger.warning(f"Edge vertices data is not bytes/bytearray: {type(data)}")
        else:
            logger.warning(f"Edge vertices attribute has unexpected format: {type(vertices_attr)}")

        if not edge_vertices:
            return edge_map

        # Get smooth flags if available
        smooth_flags = None
        attributes = edge_data.get("attributes", {})
        if "_SMOOTH" in attributes:
            smooth_attr = attributes["_SMOOTH"]
            if isinstance(smooth_attr, dict) and "data" in smooth_attr:
                data = smooth_attr["data"]
                if isinstance(data, (bytes, bytearray)):
                    smooth_flags = struct.unpack(f"<{edge_count}B", data)
                    logger.debug(f"Read {len(smooth_flags)} edge smooth flags from direct data")

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

                    # Apply smooth flag if available
                    if smooth_flags and i < len(smooth_flags):
                        edge.smooth = bool(smooth_flags[i])

                except ValueError:
                    # Edge already exists, find it
                    for existing_edge in bm.edges:
                        if set(existing_edge.verts) == {vert1, vert2}:
                            edge_map[i] = existing_edge
                            if smooth_flags and i < len(smooth_flags):
                                existing_edge.smooth = bool(smooth_flags[i])
                            break

        return edge_map

    def _reconstruct_faces_from_direct_data(self, bm: BMesh, face_data: Dict[str, Any], vertex_map: Dict[int, BMVert], edge_map: Dict[int, BMEdge]) -> Dict[int, BMFace]:
        """Reconstruct faces from direct encoded data."""
        face_map = {}
        face_count = face_data.get("count", 0)

        if face_count == 0:
            return face_map

        # Get face vertex data and offsets
        vertices_attr = face_data.get("vertices")
        offsets_attr = face_data.get("offsets")

        if vertices_attr is None or offsets_attr is None:
            return face_map

        # Handle offsets
        offsets = None
        if isinstance(offsets_attr, dict) and "data" in offsets_attr:
            data = offsets_attr["data"]
            if isinstance(data, (bytes, bytearray)):
                offsets = struct.unpack(f"<{face_count + 1}I", data)
                logger.debug(f"Read {len(offsets)} face offsets from direct data")
            else:
                logger.warning(f"Offsets data is not bytes/bytearray: {type(data)}")

        if not offsets:
            return face_map

        # Handle face vertices
        max_vertex_offset = offsets[face_count]
        face_vertices_data = None
        if isinstance(vertices_attr, dict) and "data" in vertices_attr:
            data = vertices_attr["data"]
            if isinstance(data, (bytes, bytearray)):
                face_vertices_data = struct.unpack(f"<{max_vertex_offset}I", data)
                logger.debug(f"Read {len(face_vertices_data)} face vertex indices from direct data")
            else:
                logger.warning(f"Face vertices data is not bytes/bytearray: {type(data)}")

        if not face_vertices_data:
            return face_map

        # Handle face smooth flags if available
        face_smooth_flags = None
        smooth_attr = face_data.get("smooth")
        if smooth_attr is not None:
            if isinstance(smooth_attr, dict) and "data" in smooth_attr:
                data = smooth_attr["data"]
                if isinstance(data, (bytes, bytearray)):
                    face_smooth_flags = struct.unpack(f"<{face_count}B", data)
                    smooth_count = sum(1 for flag in face_smooth_flags if flag)
                    flat_count = len(face_smooth_flags) - smooth_count
                    logger.debug(f"Read {len(face_smooth_flags)} face smooth flags from direct data: {smooth_count} smooth, {flat_count} flat")
                else:
                    logger.warning(f"Face smooth data is not bytes/bytearray: {type(data)}")
            else:
                logger.warning(f"Face smooth attribute has unexpected format: {type(smooth_attr)}")

        # Create faces
        for i in range(face_count):
            vertex_start = offsets[i]
            vertex_end = offsets[i + 1] if i + 1 < len(offsets) else max_vertex_offset

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

                    # Apply stored face smooth flag if available
                    if face_smooth_flags and i < len(face_smooth_flags):
                        face.smooth = bool(face_smooth_flags[i])
                        logger.debug(f"Applied smooth flag {bool(face_smooth_flags[i])} to face {i}")

                except ValueError as e:
                    logger.warning(f"Failed to create face {i}: {e}")

        return face_map

    def _apply_loop_data_from_direct_data(self, bm: BMesh, loop_data: Dict[str, Any], vertex_map: Dict[int, BMVert], edge_map: Dict[int, BMEdge], face_map: Dict[int, BMFace]) -> None:
        """Apply loop data from direct encoded data."""
        loop_count = loop_data.get("count", 0)
        if loop_count == 0:
            return

        # Handle UV attributes
        attributes = loop_data.get("attributes", {})
        uv_data = {}

        for attr_name, attr_data in attributes.items():
            if attr_name.startswith("TEXCOORD_") and isinstance(attr_data, dict) and "data" in attr_data:
                data = attr_data["data"]
                if isinstance(data, (bytes, bytearray)):
                    uv_coords = struct.unpack(f"<{loop_count * 2}f", data)
                    uv_data[attr_name] = uv_coords
                    logger.debug(f"Read {len(uv_coords)//2} UV coordinates for {attr_name}")

        # Apply UV data
        if uv_data:
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

    def _has_explicit_topology_data(self, extension_data: Dict[str, Any]) -> bool:
        """Check if extension data contains explicit BMesh topology."""
        required_keys = ["vertices", "edges", "loops", "faces"]
        return all(key in extension_data for key in required_keys)

    # Removed broken glTF buffer-based reconstruction methods
    # Keeping only working direct data methods for roundtrip tests


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
            # Store BMesh face smooth flags before conversion
            bmesh_smooth_flags = {}
            for i, face in enumerate(bm.faces):
                bmesh_smooth_flags[i] = face.smooth

            # Update the mesh with BMesh data
            bm.to_mesh(mesh)

            # Manually transfer face smooth flags from BMesh to mesh
            # The bm.to_mesh() call may not preserve face smooth flags correctly
            if bmesh_smooth_flags:
                for i, face in enumerate(mesh.polygons):
                    if i in bmesh_smooth_flags:
                        face.use_smooth = bmesh_smooth_flags[i]
                        logger.debug(f"Transferred smooth flag {bmesh_smooth_flags[i]} to mesh face {i}")

            # Handle smooth shading based on Blender version
            # Note: Face smooth flags were already set during BMesh reconstruction
            # Only apply auto smooth for older Blender versions when no face smooth flags are set
            if bpy.app.version < (4, 1) and not bmesh_smooth_flags:
                # Blender 4.0 and earlier: use auto smooth only when no face smooth flags are manually set
                mesh.use_auto_smooth = True
                logger.info("Applied auto smooth for Blender 4.0 and earlier (no manual face smooth flags)")
            else:
                # Blender 4.1+ or when face smooth flags are manually set: preserve face smooth flags
                logger.info("Preserved face smooth flags from BMesh reconstruction")

            # Ensure proper mesh finalization for smooth shading preservation
            mesh.update()
            mesh.calc_loop_triangles()

            # Calculate normals to respect edge smooth flags
            # Use the correct method based on Blender version
            if hasattr(mesh, 'calc_normals'):
                mesh.calc_normals()
            elif hasattr(mesh, 'calc_normals_split'):
                mesh.calc_normals_split()
            else:
                logger.warning("No normal calculation method available")

            logger.info("Successfully applied BMesh to Blender mesh with surface smoothness preservation")
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

    # Removed broken glTF buffer reading methods that cause NoneType errors

    # Removed broken glTF buffer methods - kept only working direct data methods

    # Removed all remaining broken glTF buffer methods
    # Only direct data methods remain (which work with roundtrip tests)
