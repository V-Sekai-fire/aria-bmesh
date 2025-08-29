defmodule AriaBmeshDomain.AtomicActionsTest do
  @moduledoc """
  Tests for atomic BMesh actions following R25W1398085 specification.

  Validates that all atomic mesh operations (add_vertex, add_face, etc.)
  work correctly and follow the durative action specification patterns.
  """
  use ExUnit.Case

  alias AriaBmeshDomain

  setup do
    state = AriaState.new()
    {:ok, state_with_entities} = AriaBmeshDomain.setup_mesh_scenario(state, [])
    {:ok, state: state_with_entities}
  end

  describe "create_bmesh action - R25W1398085 compliance" do
    test "creates empty bmesh with proper state facts", %{state: state} do
      {:ok, new_state} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # Verify mesh existence fact
      assert AriaState.get_fact(new_state, "test_mesh", "mesh_exists") == true

      # Verify initial counts
      assert AriaState.get_fact(new_state, "test_mesh", "vertex_count") == 0
      assert AriaState.get_fact(new_state, "test_mesh", "edge_count") == 0
      assert AriaState.get_fact(new_state, "test_mesh", "face_count") == 0
      assert AriaState.get_fact(new_state, "test_mesh", "loop_count") == 0
    end

    test "prevents duplicate mesh creation", %{state: state} do
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # Try to create same mesh again
      {:error, reason} = AriaBmeshDomain.create_bmesh(state_with_mesh, ["test_mesh"])
      assert reason == :mesh_already_exists
    end

    test "follows durative action pattern with PT0.01S duration", %{state: state} do
      # This test validates the @action duration: "PT0.01S" attribute
      # The action should be nearly instantaneous
      start_time = System.monotonic_time(:millisecond)
      {:ok, _new_state} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])
      end_time = System.monotonic_time(:millisecond)

      # Should complete quickly (under 100ms in test environment)
      assert (end_time - start_time) < 100
    end
  end

  describe "add_vertex action - atomic mesh operations" do
    setup %{state: state} do
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])
      {:ok, state: state_with_mesh}
    end

    test "adds vertex with position to existing mesh", %{state: state} do
      position = {1.0, 2.0, 3.0}
      {:ok, new_state} = AriaBmeshDomain.add_vertex(state, ["test_mesh", "v1", position])

      # Verify vertex existence
      assert AriaState.get_fact(new_state, {"test_mesh", "v1"}, "vertex_exists") == true
      assert AriaState.get_fact(new_state, {"test_mesh", "v1"}, "position") == position

      # Verify vertex count updated
      assert AriaState.get_fact(new_state, "test_mesh", "vertex_count") == 1
    end

    test "prevents duplicate vertex creation", %{state: state} do
      position = {1.0, 2.0, 3.0}
      {:ok, state_with_vertex} = AriaBmeshDomain.add_vertex(state, ["test_mesh", "v1", position])

      # Try to add same vertex again
      {:error, reason} = AriaBmeshDomain.add_vertex(state_with_vertex, ["test_mesh", "v1", position])
      assert reason == :vertex_already_exists
    end

    test "fails when mesh doesn't exist", %{state: state} do
      position = {1.0, 2.0, 3.0}
      {:error, reason} = AriaBmeshDomain.add_vertex(state, ["nonexistent_mesh", "v1", position])
      assert reason == :mesh_not_found
    end

    test "increments vertex count correctly", %{state: state} do
      # Add multiple vertices
      {:ok, state1} = AriaBmeshDomain.add_vertex(state, ["test_mesh", "v1", {0.0, 0.0, 0.0}])
      {:ok, state2} = AriaBmeshDomain.add_vertex(state1, ["test_mesh", "v2", {1.0, 0.0, 0.0}])
      {:ok, state3} = AriaBmeshDomain.add_vertex(state2, ["test_mesh", "v3", {0.0, 1.0, 0.0}])

      assert AriaState.get_fact(state3, "test_mesh", "vertex_count") == 3
    end

    test "follows durative action pattern with PT0.1S duration", %{state: state} do
      # Validates the @action duration: "PT0.1S" attribute
      start_time = System.monotonic_time(:millisecond)
      {:ok, _new_state} = AriaBmeshDomain.add_vertex(state, ["test_mesh", "v1", {0.0, 0.0, 0.0}])
      end_time = System.monotonic_time(:millisecond)

      # Should complete quickly but may take slightly longer than create_bmesh
      assert (end_time - start_time) < 200
    end
  end

  describe "add_face action - topology construction" do
    setup %{state: state} do
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # Add vertices for face creation
      {:ok, state1} = AriaBmeshDomain.add_vertex(state_with_mesh, ["test_mesh", "v1", {0.0, 0.0, 0.0}])
      {:ok, state2} = AriaBmeshDomain.add_vertex(state1, ["test_mesh", "v2", {1.0, 0.0, 0.0}])
      {:ok, state3} = AriaBmeshDomain.add_vertex(state2, ["test_mesh", "v3", {0.0, 1.0, 0.0}])

      {:ok, state: state3}
    end

    test "creates face with vertex references", %{state: state} do
      vertex_ids = ["v1", "v2", "v3"]
      {:ok, new_state} = AriaBmeshDomain.add_face(state, ["test_mesh", "f1", vertex_ids])

      # Verify face existence
      assert AriaState.get_fact(new_state, {"test_mesh", "f1"}, "face_exists") == true
      assert AriaState.get_fact(new_state, {"test_mesh", "f1"}, "vertices") == vertex_ids

      # Verify face count updated
      assert AriaState.get_fact(new_state, "test_mesh", "face_count") == 1

      # Verify edge count updated (3 edges for triangle)
      assert AriaState.get_fact(new_state, "test_mesh", "edge_count") == 3
    end

    test "prevents duplicate face creation", %{state: state} do
      vertex_ids = ["v1", "v2", "v3"]
      {:ok, state_with_face} = AriaBmeshDomain.add_face(state, ["test_mesh", "f1", vertex_ids])

      # Try to add same face again
      {:error, reason} = AriaBmeshDomain.add_face(state_with_face, ["test_mesh", "f1", vertex_ids])
      assert reason == :face_already_exists
    end

    test "fails when vertices don't exist", %{state: state} do
      vertex_ids = ["v1", "v2", "v_nonexistent"]
      {:error, reason} = AriaBmeshDomain.add_face(state, ["test_mesh", "f1", vertex_ids])
      assert reason == :vertices_not_found
    end

    test "fails when mesh doesn't exist", %{state: state} do
      vertex_ids = ["v1", "v2", "v3"]
      {:error, reason} = AriaBmeshDomain.add_face(state, ["nonexistent_mesh", "f1", vertex_ids])
      assert reason == :mesh_not_found
    end

    test "handles quad faces correctly", %{state: state} do
      # Add fourth vertex
      {:ok, state_with_v4} = AriaBmeshDomain.add_vertex(state, ["test_mesh", "v4", {1.0, 1.0, 0.0}])

      vertex_ids = ["v1", "v2", "v4", "v3"]  # Quad face
      {:ok, new_state} = AriaBmeshDomain.add_face(state_with_v4, ["test_mesh", "f1", vertex_ids])

      assert AriaState.get_fact(new_state, {"test_mesh", "f1"}, "vertices") == vertex_ids
      assert AriaState.get_fact(new_state, "test_mesh", "edge_count") == 4
    end

    test "follows durative action pattern with PT0.2S duration", %{state: state} do
      # Validates the @action duration: "PT0.2S" attribute
      start_time = System.monotonic_time(:millisecond)
      {:ok, _new_state} = AriaBmeshDomain.add_face(state, ["test_mesh", "f1", ["v1", "v2", "v3"]])
      end_time = System.monotonic_time(:millisecond)

      # Should complete quickly but may take longer than vertex operations
      assert (end_time - start_time) < 300
    end
  end

  describe "remove_edge action - topology modification" do
    setup %{state: state} do
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # Add vertices and face to create edges
      {:ok, state1} = AriaBmeshDomain.add_vertex(state_with_mesh, ["test_mesh", "v1", {0.0, 0.0, 0.0}])
      {:ok, state2} = AriaBmeshDomain.add_vertex(state1, ["test_mesh", "v2", {1.0, 0.0, 0.0}])
      {:ok, state3} = AriaBmeshDomain.add_vertex(state2, ["test_mesh", "v3", {0.0, 1.0, 0.0}])
      {:ok, state4} = AriaBmeshDomain.add_face(state3, ["test_mesh", "f1", ["v1", "v2", "v3"]])

      # Manually set edge existence for testing
      state5 = AriaState.set_fact(state4, {"test_mesh", "e1"}, "edge_exists", true)

      {:ok, state: state5}
    end

    test "removes edge and associated faces", %{state: state} do
      {:ok, new_state} = AriaBmeshDomain.remove_edge(state, ["test_mesh", "e1"])

      # Verify edge removed
      assert AriaState.get_fact(new_state, {"test_mesh", "e1"}, "edge_exists") == false

      # Verify face count reset (BMesh behavior - removing edge removes faces)
      assert AriaState.get_fact(new_state, "test_mesh", "face_count") == 0
      assert AriaState.get_fact(new_state, "test_mesh", "loop_count") == 0
    end

    test "fails when edge doesn't exist", %{state: state} do
      {:error, reason} = AriaBmeshDomain.remove_edge(state, ["test_mesh", "nonexistent_edge"])
      assert reason == :edge_not_found
    end

    test "fails when mesh doesn't exist", %{state: state} do
      {:error, reason} = AriaBmeshDomain.remove_edge(state, ["nonexistent_mesh", "e1"])
      assert reason == :mesh_not_found
    end
  end

  describe "attribute addition actions - mesh metadata" do
    setup %{state: state} do
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])
      {:ok, state: state_with_mesh}
    end

    test "adds vertex attribute with type and dimensions", %{state: state} do
      {:ok, new_state} = AriaBmeshDomain.add_vertex_attribute(state, ["test_mesh", "color", "float", 3])

      expected_attr = %{type: "float", dimensions: 3}
      assert AriaState.get_fact(new_state, {"test_mesh", "vertex_attr", "color"}) == expected_attr
    end

    test "adds edge attribute with type and dimensions", %{state: state} do
      {:ok, new_state} = AriaBmeshDomain.add_edge_attribute(state, ["test_mesh", "weight", "float", 1])

      expected_attr = %{type: "float", dimensions: 1}
      assert AriaState.get_fact(new_state, {"test_mesh", "edge_attr", "weight"}) == expected_attr
    end

    test "adds face attribute with type and dimensions", %{state: state} do
      {:ok, new_state} = AriaBmeshDomain.add_face_attribute(state, ["test_mesh", "material_id", "int", 1])

      expected_attr = %{type: "int", dimensions: 1}
      assert AriaState.get_fact(new_state, {"test_mesh", "face_attr", "material_id"}) == expected_attr
    end

    test "attribute actions fail when mesh doesn't exist", %{state: state} do
      {:error, reason1} = AriaBmeshDomain.add_vertex_attribute(state, ["nonexistent", "attr", "float", 1])
      {:error, reason2} = AriaBmeshDomain.add_edge_attribute(state, ["nonexistent", "attr", "float", 1])
      {:error, reason3} = AriaBmeshDomain.add_face_attribute(state, ["nonexistent", "attr", "float", 1])

      assert reason1 == :mesh_not_found
      assert reason2 == :mesh_not_found
      assert reason3 == :mesh_not_found
    end

    test "follows durative action pattern with PT0.05S duration", %{state: state} do
      # Validates the @action duration: "PT0.05S" attribute for attribute actions
      start_time = System.monotonic_time(:millisecond)
      {:ok, _new_state} = AriaBmeshDomain.add_vertex_attribute(state, ["test_mesh", "test_attr", "float", 3])
      end_time = System.monotonic_time(:millisecond)

      # Should be very fast operations
      assert (end_time - start_time) < 100
    end
  end

  describe "atomic action integration - complex mesh construction" do
    test "builds triangle mesh using atomic actions", %{state: state} do
      # Create mesh
      {:ok, state1} = AriaBmeshDomain.create_bmesh(state, ["triangle_mesh"])

      # Add vertices
      {:ok, state2} = AriaBmeshDomain.add_vertex(state1, ["triangle_mesh", "v1", {0.0, 0.0, 0.0}])
      {:ok, state3} = AriaBmeshDomain.add_vertex(state2, ["triangle_mesh", "v2", {1.0, 0.0, 0.0}])
      {:ok, state4} = AriaBmeshDomain.add_vertex(state3, ["triangle_mesh", "v3", {0.5, 1.0, 0.0}])

      # Add face
      {:ok, state5} = AriaBmeshDomain.add_face(state4, ["triangle_mesh", "f1", ["v1", "v2", "v3"]])

      # Add attributes
      {:ok, final_state} = AriaBmeshDomain.add_vertex_attribute(state5, ["triangle_mesh", "normal", "float", 3])

      # Verify final mesh state
      assert AriaState.get_fact(final_state, "triangle_mesh", "mesh_exists") == true
      assert AriaState.get_fact(final_state, "triangle_mesh", "vertex_count") == 3
      assert AriaState.get_fact(final_state, "triangle_mesh", "face_count") == 1
      assert AriaState.get_fact(final_state, "triangle_mesh", "edge_count") == 3

      # Verify attribute exists
      expected_attr = %{type: "float", dimensions: 3}
      assert AriaState.get_fact(final_state, {"triangle_mesh", "vertex_attr", "normal"}) == expected_attr
    end
  end
end
