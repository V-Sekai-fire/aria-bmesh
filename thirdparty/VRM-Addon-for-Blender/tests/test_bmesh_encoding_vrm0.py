"""
Test EXT_bmesh_encoding support for VRM 0.x export.
Tests encoding/decoding fidelity and proper integration with VRM 0.x exporter.
"""
import unittest
import tempfile
import json
import bpy
from pathlib import Path
import bmesh

import sys
from pathlib import Path

# Add the src directory to Python path to allow imports
test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from .base_blender_test_case import BaseBlenderTestCase
from io_scene_vrm.editor.bmesh_encoding.encoding import BmeshEncoder
from io_scene_vrm.editor.bmesh_encoding.decoding import BmeshDecoder


logger = get_logger(__name__)


class TestBmeshEncodingVrm0(BaseBlenderTestCase):
    """Test EXT_bmesh_encoding integration with VRM 0.x exporter."""

    def setUp(self):
        super().setUp()
        self.bmesh_encoder = BmeshEncoder()
        self.bmesh_decoder = BmeshDecoder()

    def create_test_mesh_object(self, name="TestMesh", topology_type="cube"):
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

    def test_export_ext_bmesh_encoding_parameter(self):
        """Test that VRM 0.x exporter accepts and uses export_ext_bmesh_encoding parameter."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object()

        # Test with EXT_bmesh_encoding enabled
        exporter_enabled = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        # Test with EXT_bmesh_encoding disabled
        exporter_disabled = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=False
        )

        self.assertTrue(exporter_enabled.export_ext_bmesh_encoding)
        self.assertFalse(exporter_disabled.export_ext_bmesh_encoding)

    def test_ext_bmesh_encoding_extension_in_output(self):
        """Test that EXT_bmesh_encoding extension appears in glTF output when enabled."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object("TestMesh", "ico_sphere")

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed")

        # Parse the glb result
        glb_data = result
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Check that EXT_bmesh_encoding is in extensionsUsed
        self.assertIn("EXT_bmesh_encoding", gltf_data.get("extensionsUsed", []),
                     "EXT_bmesh_encoding should be in extensionsUsed when enabled")

        # Find the mesh and check for extension
        meshes = gltf_data.get("meshes", [])
        found_extension = False
        for mesh in meshes:
            if mesh.get("name") == obj.data.name or mesh.get("name") == obj.name:
                primitives = mesh.get("primitives", [])
                for primitive in primitives:
                    extensions = primitive.get("extensions", {})
                    if "EXT_bmesh_encoding" in extensions:
                        found_extension = True
                        break
                break

        self.assertTrue(found_extension, "EXT_bmesh_encoding should be present in mesh primitives")

    def test_ext_bmesh_encoding_disabled_behavior(self):
        """Test that EXT_bmesh_encoding extension does not appear when disabled."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object("TestMesh", "complex")

        # Export with EXT_bmesh_encoding disabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=False
        )

        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed")

        # Parse the glb result
        glb_data = result
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Check that EXT_bmesh_encoding is NOT in extensionsUsed
        extensions_used = gltf_data.get("extensionsUsed", [])
        self.assertNotIn("EXT_bmesh_encoding", extensions_used,
                        "EXT_bmesh_encoding should not be in extensionsUsed when disabled")

        # Verify no mesh primitives have the extension
        meshes = gltf_data.get("meshes", [])
        for mesh in meshes:
            if mesh.get("name") == obj.data.name or mesh.get("name") == obj.name:
                primitives = mesh.get("primitives", [])
                for primitive in primitives:
                    extensions = primitive.get("extensions", {})
                    self.assertNotIn("EXT_bmesh_encoding", extensions,
                                   "EXT_bmesh_encoding should not be in primitive extensions when disabled")

    def test_bmesh_encoding_fidelity_cube(self):
        """Test encoding/decoding fidelity for a simple cube mesh."""
        obj = self.create_test_mesh_object("CubeMesh", "cube")

        # Encode the mesh
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed")

        # Test that encoded data contains expected structures
        self.assertIn("vertex", encoded_data, "Encoded data should contain vertex information")
        self.assertIn("face", encoded_data, "Encoded data should contain face information")
        self.assertIn("loop", encoded_data, "Encoded data should contain loop information")

        # Decode and compare
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed")

        # Compare basic properties
        original_mesh = obj.data
        self.assertEqual(len(original_mesh.vertices), len(decoded_mesh.vertices),
                        "Number of vertices should match")
        self.assertEqual(len(original_mesh.polygons), len(decoded_mesh.polygons),
                        "Number of faces should match")

    def test_bmesh_encoding_fidelity_sphere(self):
        """Test encoding/decoding fidelity for an icosphere with complex topology."""
        obj = self.create_test_mesh_object("SphereMesh", "ico_sphere")

        # Encode the mesh
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed for complex topology")

        # Decode and compare
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed for complex topology")

        original_mesh = obj.data
        # For an icosphere, we expect the same number of vertices and faces
        self.assertEqual(len(original_mesh.vertices), len(decoded_mesh.vertices),
                        "Vertex count should match for sphere")
        self.assertEqual(len(original_mesh.polygons), len(decoded_mesh.polygons),
                        "Face count should match for sphere")

    def test_bmesh_encoding_fidelity_complex_mesh(self):
        """Test encoding/decoding fidelity for a complex mesh with mixed topology."""
        obj = self.create_test_mesh_object("ComplexMesh", "complex")

        # Encode the mesh
        encoded_data = self.bmesh_encoder.encode_object_native(obj)
        self.assertIsNotNone(encoded_data, "Encoding should succeed for mixed topology")

        # Decode and compare
        decoded_mesh = self.bmesh_decoder.decode_into_mesh(encoded_data)
        self.assertIsNotNone(decoded_mesh, "Decoding should succeed for mixed topology")

        original_mesh = obj.data
        self.assertEqual(len(original_mesh.vertices), len(decoded_mesh.vertices),
                        "Vertex count should match for complex mesh")
        self.assertEqual(len(original_mesh.polygons), len(decoded_mesh.polygons),
                        "Face count should match for complex mesh")

    def test_ext_bmesh_encoding_buffer_view_creation(self):
        """Test that buffer views are properly created for EXT_bmesh_encoding data."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object("BufferTestMesh", "ico_sphere")

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed")

        # Parse the glb result
        glb_data = result
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Find EXT_bmesh_encoding data in mesh primitives
        meshes = gltf_data.get("meshes", [])
        ext_bmesh_data = None
        for mesh in meshes:
            primitives = mesh.get("primitives", [])
            for primitive in primitives:
                extensions = primitive.get("extensions", {})
                if "EXT_bmesh_encoding" in extensions:
                    ext_bmesh_data = extensions["EXT_bmesh_encoding"]
                    break
            if ext_bmesh_data:
                break

        self.assertIsNotNone(ext_bmesh_data, "Should find EXT_bmesh_encoding data")

        # Verify buffer views are referenced
        buffer_views = gltf_data.get("bufferViews", [])
        if ext_bmesh_data:
            # Check that all referenced buffer views exist
            for key, accessor_index in ext_bmesh_data.items():
                if isinstance(accessor_index, int):
                    if key.endswith("Accessor"):
                        accessor = gltf_data.get("accessors", [])[accessor_index]
                        buffer_view_index = accessor.get("bufferView")
                        self.assertIsNotNone(buffer_view_index, f"Accessor {accessor_index} should have bufferView")
                        self.assertLess(buffer_view_index, len(buffer_views),
                                       f"Buffer view index {buffer_view_index} should exist")

    def test_ext_bmesh_encoding_multiple_meshes(self):
        """Test EXT_bmesh_encoding with multiple meshes in the same export."""
        armature = self.create_humanoid_armature()

        # Create multiple mesh objects
        obj1 = self.create_test_mesh_object("Mesh1", "cube")
        obj2 = self.create_test_mesh_object("Mesh2", "ico_sphere")
        obj3 = self.create_test_mesh_object("Mesh3", "complex")

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj1, obj2, obj3],
            armature,
            export_ext_bmesh_encoding=True
        )

        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed with multiple meshes")

        # Parse the glb result
        glb_data = result
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Verify EXT_bmesh_encoding extension is present
        self.assertIn("EXT_bmesh_encoding", gltf_data.get("extensionsUsed", []))

        # Count meshes with EXT_bmesh_encoding
        meshes = gltf_data.get("meshes", [])
        ext_bmesh_count = 0
        for mesh in meshes:
            primitives = mesh.get("primitives", [])
            for primitive in primitives:
                if "EXT_bmesh_encoding" in primitive.get("extensions", {}):
                    ext_bmesh_count += 1
                    break

        # Should have extensions in all 3 meshes
        self.assertEqual(ext_bmesh_count, 3, "All meshes should have EXT_bmesh_encoding when enabled")

    def test_ext_bmesh_encoding_backwards_compatibility(self):
        """Test that exporting without EXT_bmesh_encoding produces compatible output."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object("CompatMesh", "ico_sphere")

        # Export with EXT_bmesh_encoding disabled
        exporter_disabled = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=False
        )

        result_disabled = exporter_disabled.export_vrm()
        self.assertIsNotNone(result_disabled, "Export should succeed without EXT_bmesh_encoding")

        # Parse and verify valid glTF
        glb_data = result_disabled
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Verify no EXT_bmesh_encoding
        self.assertNotIn("EXT_bmesh_encoding", gltf_data.get("extensionsUsed", []))

        # Verify standard VRM 0.x structure is present
        self.assertIn("extensions", gltf_data)
        self.assertIn("VRM", gltf_data["extensions"])
        self.assertEqual(gltf_data["extensions"]["VRM"]["specVersion"], "0.0")

        # Verify meshes exist and are valid
        meshes = gltf_data.get("meshes", [])
        self.assertGreater(len(meshes), 0, "Should have at least one mesh")

    def test_ext_bmesh_encoding_edge_case_empty_mesh(self):
        """Test EXT_bmesh_encoding handling of edge cases like empty meshes."""
        armature = self.create_humanoid_armature()

        # Add an empty mesh object (no geometry)
        obj = bpy.data.objects.new("EmptyMesh", bpy.data.meshes.new("EmptyMesh"))
        bpy.context.collection.objects.link(obj)

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        # This should not fail even with empty mesh
        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed even with empty mesh")

    def test_ext_bmesh_encoding_edge_case_multiple_materials(self):
        """Test EXT_bmesh_encoding with meshes having multiple materials."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object("MultiMatMesh", "cube")

        # Add a second material
        mat2 = bpy.data.materials.new("Material2")
        obj.data.materials.append(mat2)

        # Split faces between materials
        for i, face in enumerate(obj.data.polygons):
            face.material_index = i % 2

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed with multiple materials")

        # Parse and verify
        glb_data = result
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Verify EXT_bmesh_encoding is present
        self.assertIn("EXT_bmesh_encoding", gltf_data.get("extensionsUsed", []))

    def test_ext_bmesh_encoding_mesh_with_shape_keys(self):
        """Test EXT_bmesh_encoding with meshes that have shape keys."""
        armature = self.create_humanoid_armature()
        obj = self.create_test_mesh_object("ShapeMesh", "cube")

        # Add a shape key
        shape_key = obj.shape_key_add(name="Deformed")
        shape_key.keyframe_insert("value", frame=1)

        # Modify the shape key
        for i, vert in enumerate(shape_key.data):
            vert.co = vert.co + (0.1 * i, 0.1 * i, 0.1 * i)

        # Export with EXT_bmesh_encoding enabled
        exporter = Vrm0Exporter(
            bpy.context,
            [obj],
            armature,
            export_ext_bmesh_encoding=True
        )

        result = exporter.export_vrm()
        self.assertIsNotNone(result, "Export should succeed with shape keys")

        # Parse and verify
        glb_data = result
        json_start = glb_data.find(b'{')
        json_end = glb_data.rfind(b'}') + 1
        json_str = glb_data[json_start:json_end].decode('utf-8')
        gltf_data = json.loads(json_str)

        # Verify EXT_bmesh_encoding with shape keys
        self.assertIn("EXT_bmesh_encoding", gltf_data.get("extensionsUsed", []))


if __name__ == "__main__":
    unittest.main()
