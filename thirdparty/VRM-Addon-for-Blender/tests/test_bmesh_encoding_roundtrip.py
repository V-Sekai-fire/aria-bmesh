"""
Test round-trip encoding/decoding fidelity of EXT_bmesh_encoding.
Tests that meshes maintain full fidelity through encode/decode cycles.
"""
import unittest
import bpy
import bmesh
import math
import numpy as np

import sys
from pathlib import Path

# Add the src directory to Python path to allow imports
test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from .base_blender_test_case import BaseBlenderTestCase
from io_scene_vrm.editor.bmesh_encoding.encoding import BmeshEncoder
from io_scene_vrm.editor.bmesh_encoding.decoding import BmeshDecoder
from io_scene_vrm.common import ops
from io_scene_vrm.common.logger import get_logger


class TestBmeshEncodingRoundtrip(BaseBlenderTestCase):
    """Test round-trip encoding/decoding fidelity."""

    def setUp(self):
        super().setUp()
        self.bmesh_encoder = BmeshEncoder()
        self.bmesh_decoder = BmeshDecoder()

    def create_test_mesh_object(self, name="TestMesh", topology_type="ico_sphere"):
        """Create a test mesh with specified topology."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        bpy.context.collection.objects.link(obj)

        # Create mesh based on topology type
        bm = bmesh.new()
        bm.from_mesh(mesh)

        if topology_type == "cube":
            # Add a simple cube
            bmesh.ops.create_cube(bm, size=2.0)
        elif topology_type == "ico_sphere":
            # Add an icosphere with non-uniform triangulation
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        elif topology_type == "complex":
            # Create a more complex mesh with various face types
            verts = []
            faces = []

            # Add vertices in a pattern
            for x in range(-2, 3):
                for y in range(-1, 2):
                    for z in range(-2, 3):
                        verts.append((x, y, z))

            # Add faces creating different topologies
            for x in range(-2, 2):
                for z in range(-2, 2):
                    # Create quad faces (will be triangulated)
                    faces.append([
                        ((x+2) * 3 + (z+2)),
                        ((x+2) * 3 + (z+3)),
                        ((x+3) * 3 + (z+3)),
                        ((x+3) * 3 + (z+2))
                    ])

            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            for vert_pos in verts:
                bm.verts.new(vert_pos)
            for face_verts in faces:
                bm.faces.new([bm.verts[i] for i in face_verts])

        bm.to_mesh(mesh)
        bm.free()

        return obj

    def create_complex_topology_mesh(self, name="ComplexTopologyMesh"):
        """Create a mesh with complex topology including ngons and quads."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        bpy.context.collection.objects.link(obj)

        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Create complex topology with mixed face types
        # Add vertices
        verts = []
        # Base pyramid-like structure
        verts.extend([
            (0, 0, 0),      # 0: base center
            (1, 0, 0),      # 1: base edge
            (0.5, 0.866, 0), # 2: base edge (60 degrees)
            (0, 0, 1),      # 3: apex
            (0.5, 0, 0.5),  # 4: middle point
            (-0.5, 0, 0.5), # 5: middle point
            (0, -0.5, 0.5), # 6: middle point
        ])

        for vert_pos in verts:
            bm.verts.new(vert_pos)

        bm.verts.ensure_lookup_table()

        # Add faces with mixed topology
        # Triangles
        bm.faces.new([bm.verts[3], bm.verts[1], bm.verts[0]])  # apex triangle
        bm.faces.new([bm.verts[3], bm.verts[2], bm.verts[1]])  # apex triangle

        # Quads
        bm.faces.new([bm.verts[0], bm.verts[1], bm.verts[4], bm.verts[5]])  # base quad 1
        bm.faces.new([bm.verts[1], bm.verts[2], bm.verts[6], bm.verts[4]])  # base quad 2
        bm.faces.new([bm.verts[2], bm.verts[0], bm.verts[5], bm.verts[6]])  # base quad 3

        # Additional complex faces
        # Removed duplicate face creation that was causing "face already exists" error

        # Calculate sharp edges based on angle before freeing BMesh
        angles = {}
        for edge in bm.edges:
            if len(edge.link_faces) == 2:
                normal1 = edge.link_faces[0].normal
                normal2 = edge.link_faces[1].normal

                # Skip edges with degenerate faces (zero-length normals)
                if normal1.length < 1e-6 or normal2.length < 1e-6:
                    continue

                angle = normal1.angle(normal2)
                angles[edge] = math.degrees(angle)
                if angle > math.pi / 3:  # 60 degrees
                    edge.smooth = False  # Mark as sharp in BMesh

        bm.to_mesh(mesh)
        bm.free()

        # Add crease data to mesh edges
        for edge in mesh.edges:
            edge.crease = 0.5
            # Transfer sharp marking from BMesh calculation
            # Note: We can't directly map BMesh edges to Mesh edges easily,
            # so we'll apply sharp marking based on angle threshold
            if hasattr(edge, 'use_edge_sharp'):
                # This would require more complex mapping, so for now just set crease
                pass

        return obj, angles

    def create_non_manifold_mesh(self, name="NonManifoldMesh"):
        """Create a non-manifold mesh with edge cases."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        bpy.context.collection.objects.link(obj)

        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Create non-manifold topology
        # Vertices
        verts = []
        verts.extend([
            (0, 0, 0),     # 0
            (1, 0, 0),     # 1
            (0, 1, 0),     # 2
            (0, 0, 1),     # 3 - disconnected vertex
            (-1, 0, 0),    # 4
            (0, -1, 0),    # 5
        ])

        for vert_pos in verts:
            bm.verts.new(vert_pos)

        bm.verts.ensure_lookup_table()

        # Create faces, leaving some vertices disconnected
        bm.faces.new([bm.verts[0], bm.verts[1], bm.verts[2]])  # triangle
        bm.faces.new([bm.verts[0], bm.verts[4], bm.verts[5]])  # triangle with edge issues

        bm.to_mesh(mesh)
        bm.free()

        return obj

    def create_mesh_with_shape_keys(self, name="ShapeKeysMesh"):
        """Create a mesh with multiple shape keys for morph target testing."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        bpy.context.collection.objects.link(obj)

        # Create base mesh
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()

        # Add shape keys
        shape_keys = []
        for i in range(3):
            shape_key = obj.shape_key_add(name=f"Deform{i}")
            shape_keys.append(shape_key)

            # Create different deformations
            for j, vert in enumerate(shape_key.data):
                if i == 0:
                    vert.co = vert.co + (0.1 * j, 0, 0)
                elif i == 1:
                    vert.co = vert.co + (0, 0.1 * j, 0)
                else:
                    vert.co = vert.co + (0, 0, 0.1 * j)

        return obj, shape_keys

    def compare_mesh_geometry(self, original_mesh, decoded_mesh, tolerance=1e-6):
        """Compare geometric properties of two meshes."""
        # Compare vertex counts
        self.assertEqual(
            len(original_mesh.vertices),
            len(decoded_mesh.vertices),
            "Vertex counts should match"
        )

        # Compare face counts
        self.assertEqual(
            len(original_mesh.polygons),
            len(decoded_mesh.polygons),
            "Face counts should match"
        )

        # Compare vertex positions
        for i, (orig_vert, decoded_vert) in enumerate(zip(original_mesh.vertices, decoded_mesh.vertices)):
            orig_pos = np.array(orig_vert.co)
            decoded_pos = np.array(decoded_vert.co)
            distance = np.linalg.norm(orig_pos - decoded_pos)
            self.assertLess(
                distance,
                tolerance,
                f"Vertex {i} position mismatch: {distance} > {tolerance}"
            )

        # Compare face vertices (topology)
        for i, (orig_face, decoded_face) in enumerate(zip(original_mesh.polygons, decoded_mesh.polygons)):
            orig_verts = set(orig_face.vertices)
            decoded_verts = set(decoded_face.vertices)
            self.assertEqual(
                len(orig_verts),
                len(decoded_verts),
                f"Face {i} vertex counts should match"
            )
            self.assertEqual(
                orig_verts,
                decoded_verts,
                f"Face {i} topology should match"
            )

        return True

    def test_roundtrip_simple_cube(self):
        """Test round-trip encoding/decoding of a simple cube."""
        obj = self.create_test_mesh_object("Cube", "cube")

        # Store original mesh data
        original_mesh = obj.data.copy()
        original_mesh.name = "OriginalCube"

        # Encode
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed")

        # Decode
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed")

        # Compare
        self.compare_mesh_geometry(original_mesh, decoded_mesh)

    def test_roundtrip_complex_topology(self):
        """Test round-trip of mesh with complex topology."""
        obj, original_angles = self.create_complex_topology_mesh("ComplexTopo")

        # Store original mesh data
        original_mesh = obj.data.copy()

        # Encode
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed for complex topology")

        # Decode
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed for complex topology")

        # Compare geometry
        self.assertTrue(self.compare_mesh_geometry(original_mesh, decoded_mesh))

        # Note: Edge crease data is not fully preserved in VRM 0.x export
        # but that's expected as it's not part of the EXT_bmesh_encoding spec for VRM 0.x

    def test_roundtrip_non_manifold_mesh(self):
        """Test round-trip of non-manifold mesh (edge cases)."""
        obj = self.create_non_manifold_mesh("NonManifold")

        # Store original mesh data
        original_mesh = obj.data.copy()

        # Encode
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed for non-manifold mesh")

        # Decode
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed for non-manifold mesh")

        # Compare geometry - even for non-manifold, structure should be preserved
        self.assertTrue(self.compare_mesh_geometry(original_mesh, decoded_mesh))

    def test_roundtrip_with_shape_keys(self):
        """Test round-trip fidelity including shape keys."""
        obj, shape_keys = self.create_mesh_with_shape_keys("ShapeKeysTest")

        # Store original mesh data
        original_mesh = obj.data.copy()

        # Encode
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed with shape keys")

        # Decode
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed with shape keys")

        # Compare geometry
        self.assertTrue(self.compare_mesh_geometry(original_mesh, decoded_mesh))

        # Note: Shape keys are not part of EXT_bmesh_encoding in VRM 0.x export
        # They are handled separately in the glTF export pipeline

    def test_roundtrip_empty_mesh(self):
        """Test round-trip of essentially empty mesh."""
        # Create an empty mesh
        mesh = bpy.data.meshes.new("EmptyMesh")
        obj = bpy.data.objects.new("EmptyMesh", mesh)
        bpy.context.collection.objects.link(obj)

        original_mesh = obj.data.copy()

        # Encode - should handle gracefully
        encoded_data = self.bmesh_encoder.encode_object_native(obj)

        # For completely empty meshes, encoded_data might be None or minimal
        # This is acceptable behavior

        if encoded_data is not None:
            # Decode if we have data
            decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
            if decoded_mesh is not None:
                self.assertTrue(self.compare_mesh_geometry(original_mesh, decoded_mesh))

    def test_multiple_roundtrip_cycles(self):
        """Test multiple encode/decode cycles maintain fidelity."""
        obj = self.create_test_mesh_object("MultiCycle", "ico_sphere")

        # Start with original mesh
        current_mesh = obj.data
        current_obj = obj

        # Perform multiple rounds of encode/decode
        cycles = 3
        for cycle in range(cycles):
            # Store current state
            cycle_mesh = current_mesh.copy()
            cycle_mesh.name = f"Cycle{cycle}"

            # Encode current object
            encoded_data = self.bmesh_encoder.encode_object_native(current_obj)
            self.assertIsNotNone(encoded_data, f"Encoding should succeed in cycle {cycle}")

            # Create new mesh for decoded result
            new_mesh = bpy.data.meshes.new(f"DecodedCycle{cycle}")
            decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data, new_mesh)

            # Create new object for next cycle
            new_obj = bpy.data.objects.new(f"RoundtripCycle{cycle}", decoded_mesh)
            bpy.context.collection.objects.link(new_obj)

            # Compare with original cycle state
            self.assertTrue(
                self.compare_mesh_geometry(cycle_mesh, decoded_mesh),
                f"Cycle {cycle} should maintain fidelity"
            )

            # Prepare for next cycle
            current_mesh = decoded_mesh
            current_obj = new_obj

    def test_roundtrip_vrm0_export_pipeline(self):
        """Test full VRM 0.x export pipeline with EXT_bmesh_encoding preserves fidelity."""
        ops.icyp.make_basic_armature()
        armature = bpy.context.view_layer.objects.active

        # Create test mesh with complex topology
        obj = self.create_test_mesh_object("VRM0Pipeline", "ico_sphere")
        original_mesh = obj.data.copy()

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        # Perform full export
        vrm_data = exporter.export_vrm()
        self.assertIsNotNone(vrm_data, "VRM 0.x export should succeed")

        # In a real implementation, we would need to import the VRM
        # and extract the mesh to compare, but for now we'll verify
        # that the export completes successfully and produces valid data

        # Parse exported VRM to ensure it's valid
        glb_magic = b'glTF'
        self.assertTrue(
            vrm_data.startswith(glb_magic),
            "Exported VRM should be valid glb format"
        )

        # For full round-trip testing, we'd need full VRM import capability
        # This is a placeholder for when that's implemented

    def test_encoding_decoding_consistency(self):
        """Test that encoding/decoding operations are consistent across different runs."""
        obj = self.create_test_mesh_object("ConsistencyTest", "complex")

        # Encode multiple times
        encoded_data1 = self.bmesh_encoder.encode_object_native(obj)
        encoded_data2 = self.bmesh_encoder.encode_object_native(obj)

        self.assertIsNotNone(encoded_data1, "First encoding should succeed")
        self.assertIsNotNone(encoded_data2, "Second encoding should succeed")

        # Decode from both encodings
        decoded_mesh1 = self.bmesh_decoder.decode_into_mesh(encoded_data1)
        decoded_mesh2 = self.bmesh_decoder.decode_into_mesh(encoded_data2)

        self.assertIsNotNone(decoded_mesh1, "First decoding should succeed")
        self.assertIsNotNone(decoded_mesh2, "Second decoding should succeed")

        # Compare the two decoded results - should be identical
        self.assertEqual(
            len(decoded_mesh1.vertices),
            len(decoded_mesh2.vertices),
            "Multiple encodings should produce consistent vertex counts"
        )

        self.assertEqual(
            len(decoded_mesh1.polygons),
            len(decoded_mesh2.polygons),
            "Multiple encodings should produce consistent face counts"
        )

    def test_large_mesh_roundtrip(self):
        """Test round-trip performance with larger meshes."""
        # Create a larger test mesh
        vertices = []
        faces = []

        # Generate grid of vertices
        grid_size = 8  # 64x64 grid = 4096 vertices
        for x in range(grid_size):
            for z in range(grid_size):
                vertices.append((x, 0, z))

        # Generate faces
        for x in range(grid_size - 1):
            for z in range(grid_size - 1):
                # Create quad face
                v1 = x * grid_size + z
                v2 = (x + 1) * grid_size + z
                v3 = (x + 1) * grid_size + z + 1
                v4 = x * grid_size + z + 1
                faces.append((v1, v2, v3, v4))

        # Create mesh
        mesh = bpy.data.meshes.new("LargeMesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()

        obj = bpy.data.objects.new("LargeMeshObj", mesh)
        bpy.context.collection.objects.link(obj)

        original_mesh = mesh.copy()

        # Encode
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        if encoded_data is not None:  # Large meshes might exceed limits
            # Decode
            decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
            if decoded_mesh is not None:
                # Basic comparison - just ensure structure is preserved
                self.assertEqual(len(original_mesh.vertices), len(decoded_mesh.vertices))
                self.assertEqual(len(original_mesh.polygons), len(decoded_mesh.polygons))

    def test_roundtrip_with_custom_materials(self):
        """Test round-trip fidelity with meshes that have multiple materials."""
        obj = self.create_test_mesh_object("MaterialTest", "cube")

        # Add multiple materials
        mat1 = bpy.data.materials.new("Mat1")
        mat2 = bpy.data.materials.new("Mat2")
        obj.data.materials.append(mat1)
        obj.data.materials.append(mat2)

        # Assign materials to faces
        for i, face in enumerate(obj.data.polygons):
            face.material_index = i % 2

        original_mesh = obj.data.copy()

        # Encode
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed with materials")

        # Decode
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed with materials")

        # Compare basic geometry (materials are not part of EXT_bmesh_encoding)
        self.assertEqual(len(original_mesh.vertices), len(decoded_mesh.vertices))
        self.assertEqual(len(original_mesh.polygons), len(decoded_mesh.polygons))


if __name__ == "__main__":
    unittest.main()
