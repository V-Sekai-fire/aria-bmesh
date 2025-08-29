defmodule AriaBmeshDomain.IntegrationWorkflowTest do
  @moduledoc """
  Integration and workflow tests following R25W1398085 specification.

  Tests complex mesh generation workflows, multi-step task decomposition,
  goal achievement chains, and planning with multiple entities.
  """
  use ExUnit.Case

  alias AriaBmeshDomain
  alias AriaBmeshDomain.Primitives

  setup do
    state = AriaState.new()
    {:ok, state_with_entities} = AriaBmeshDomain.setup_mesh_scenario(state, [])
    {:ok, state: state_with_entities}
  end

  describe "complete mesh generation workflows" do
    test "end-to-end cuboid creation workflow", %{state: state} do
      # Test complete workflow from task method to final mesh
      {:ok, actions} = Primitives.create_cuboid_task(state, ["workflow_cuboid", %{width: 2.0, height: 2.0, depth: 2.0}])

      # Execute the action sequence step by step
      final_state = Enum.reduce(actions, state, fn action, current_state ->
        case action do
          {:create_bmesh, [mesh_id]} ->
            {:ok, new_state} = AriaBmeshDomain.create_bmesh(current_state, [mesh_id])
            new_state

          {:add_vertex, [mesh_id, vertex_id, position]} ->
            {:ok, new_state} = AriaBmeshDomain.add_vertex(current_state, [mesh_id, vertex_id, position])
            new_state

          {:add_face, [mesh_id, face_id, vertex_list]} ->
            {:ok, new_state} = AriaBmeshDomain.add_face(current_state, [mesh_id, face_id, vertex_list])
            new_state

          _ ->
            current_state
        end
      end)

      # Verify final mesh state
      assert AriaState.get_fact(final_state, "workflow_cuboid", "mesh_exists") == true
      assert AriaState.get_fact(final_state, "workflow_cuboid", "vertex_count") == 8
      assert AriaState.get_fact(final_state, "workflow_cuboid", "face_count") == 6
    end

    test "end-to-end cylinder creation workflow", %{state: state} do
      # Test cylinder workflow with custom parameters
      params = %{radius: 1.5, height: 3.0, radial_segments: 6}
      {:ok, actions} = Primitives.create_cylinder_task(state, ["workflow_cylinder", params])

      # Execute actions and verify intermediate states
      mesh_created = false
      vertices_added = 0
      faces_added = 0

      {final_state, _stats} = Enum.reduce(actions, {state, {mesh_created, vertices_added, faces_added}},
        fn action, {current_state, {mesh_created, vertices_added, faces_added}} ->
          case action do
            {:create_bmesh, [mesh_id]} ->
              {:ok, new_state} = AriaBmeshDomain.create_bmesh(current_state, [mesh_id])
              {new_state, {true, vertices_added, faces_added}}

            {:add_vertex, [mesh_id, vertex_id, position]} ->
              {:ok, new_state} = AriaBmeshDomain.add_vertex(current_state, [mesh_id, vertex_id, position])
              {new_state, {mesh_created, vertices_added + 1, faces_added}}

            {:add_face, [mesh_id, face_id, vertex_list]} ->
              {:ok, new_state} = AriaBmeshDomain.add_face(current_state, [mesh_id, face_id, vertex_list])
              {new_state, {mesh_created, vertices_added, faces_added + 1}}

            _ ->
              {current_state, {mesh_created, vertices_added, faces_added}}
          end
        end)

      # Verify final cylinder state
      assert AriaState.get_fact(final_state, "workflow_cylinder", "mesh_exists") == true
      assert AriaState.get_fact(final_state, "workflow_cylinder", "vertex_count") == 14  # 6 bottom + 6 top + 2 centers
      assert AriaState.get_fact(final_state, "workflow_cylinder", "face_count") == 18   # 6 bottom + 6 top + 6 side
    end

    test "complex ellipsoid workflow with high resolution", %{state: state} do
      # Test high-complexity primitive workflow
      params = %{radius_x: 2.0, radius_y: 1.0, radius_z: 0.5, u_segments: 12, v_segments: 8}
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["complex_ellipsoid", params])

      # Verify action sequence structure
      assert length(actions) > 100  # Should have many actions for high resolution

      # First action should be mesh creation
      assert {:create_bmesh, ["complex_ellipsoid"]} == hd(actions)

      # Should have many vertex and face actions
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)

      assert length(vertex_actions) > 90   # 12 * 8 = 96 vertices expected
      assert length(face_actions) > 80    # Many faces for high resolution
    end
  end

  describe "multi-step task decomposition workflows" do
    test "procedural mesh generation with complexity levels", %{state: state} do
      # Test low complexity procedural generation
      {:ok, low_actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["low_mesh", :low, :cuboid])

      # Should decompose into cuboid task method
      assert is_list(low_actions)
      assert length(low_actions) >= 2

      # Test medium complexity procedural generation
      {:ok, medium_actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["medium_mesh", :medium, :cylinder])

      # Should decompose into cylinder task method
      assert is_list(medium_actions)
      assert length(medium_actions) >= 2

      # Test high complexity procedural generation
      {:ok, high_actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["high_mesh", :high, :ellipsoid])

      # Should decompose into ellipsoid task method
      assert is_list(high_actions)
      assert length(high_actions) >= 2
    end

    test "nested task method decomposition", %{state: state} do
      # Test that generate_procedural_mesh properly delegates to primitive task methods
      {:ok, actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["nested_test", :low, :pyramid])

      # Should contain the same actions as direct pyramid task method call
      {:ok, direct_actions} = Primitives.create_pyramid_task(state, ["nested_test", %{base_width: 2.0, height: 2.0}])

      # The actions should be similar (may have additional quality goals)
      action_types = Enum.map(actions, fn
        {action, _args} -> action
        {pred, _subj, _val} -> pred
        other -> other
      end)

      direct_action_types = Enum.map(direct_actions, fn {action, _args} -> action end)

      # Should contain all the direct actions
      for action_type <- direct_action_types do
        assert action_type in action_types
      end
    end

    test "task method parameter propagation", %{state: state} do
      # Test that parameters are properly passed through task method chains
      {:ok, actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["param_test", :low, :triangular_prism])

      # Should generate triangular prism actions
      action_types = Enum.map(actions, fn
        {action, _args} -> action
        {pred, _subj, _val} -> pred
        other -> other
      end)

      assert :create_bmesh in action_types
      assert :add_vertex in action_types
      assert :add_face in action_types
    end
  end

  describe "goal achievement chains" do
    test "mesh existence goal achievement chain", %{state: state} do
      # Test achieving mesh existence goal
      {:ok, actions} = AriaBmeshDomain.achieve_mesh_existence(state, {"goal_mesh", true})

      # Should return action to create mesh
      assert length(actions) == 1
      assert {:create_bmesh, ["goal_mesh"]} in actions

      # Execute the action
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["goal_mesh"])

      # Now goal should be satisfied
      {:ok, no_actions} = AriaBmeshDomain.achieve_mesh_existence(state_with_mesh, {"goal_mesh", true})
      assert no_actions == []
    end

    test "vertex count goal achievement chain", %{state: state} do
      # Create initial mesh
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["vertex_goal_mesh"])

      # Test achieving vertex count goal
      {:ok, actions} = AriaBmeshDomain.achieve_vertex_count(state_with_mesh, {"vertex_goal_mesh", 12})

      # Should return topology modification action
      assert length(actions) == 1
      assert {:modify_topology, ["vertex_goal_mesh", %{add_vertices: 12}]} in actions

      # Execute the action
      {:ok, modified_state} = AriaBmeshDomain.modify_topology(state_with_mesh, ["vertex_goal_mesh", %{add_vertices: 12}])

      # Verify vertex count
      assert AriaState.get_fact(modified_state, "vertex_goal_mesh", "vertex_count") == 12

      # Now goal should be satisfied
      {:ok, no_actions} = AriaBmeshDomain.achieve_vertex_count(modified_state, {"vertex_goal_mesh", 12})
      assert no_actions == []
    end

    test "chained goal achievement workflow", %{state: state} do
      # Test achieving multiple goals in sequence

      # Goal 1: Mesh existence
      {:ok, existence_actions} = AriaBmeshDomain.achieve_mesh_existence(state, {"chain_mesh", true})
      {:ok, state1} = AriaBmeshDomain.create_bmesh(state, ["chain_mesh"])

      # Goal 2: Vertex count
      {:ok, vertex_actions} = AriaBmeshDomain.achieve_vertex_count(state1, {"chain_mesh", 8})
      {:ok, state2} = AriaBmeshDomain.modify_topology(state1, ["chain_mesh", %{add_vertices: 8}])

      # Goal 3: Additional vertices
      {:ok, more_vertex_actions} = AriaBmeshDomain.achieve_vertex_count(state2, {"chain_mesh", 16})
      {:ok, final_state} = AriaBmeshDomain.modify_topology(state2, ["chain_mesh", %{add_vertices: 8}])

      # Verify final state
      assert AriaState.get_fact(final_state, "chain_mesh", "mesh_exists") == true
      assert AriaState.get_fact(final_state, "chain_mesh", "vertex_count") == 16

      # Verify action sequences
      assert {:create_bmesh, ["chain_mesh"]} in existence_actions
      assert {:modify_topology, ["chain_mesh", %{add_vertices: 8}]} in vertex_actions
      assert {:modify_topology, ["chain_mesh", %{add_vertices: 8}]} in more_vertex_actions
    end
  end

  describe "planning with multiple entities" do
    test "entity availability and capability checking", %{state: state} do
      # Verify all required entities are available
      assert AriaState.get_fact(state, "mesh_generator", "status") == "available"
      assert AriaState.get_fact(state, "spatial_analyzer", "status") == "available"
      assert AriaState.get_fact(state, "mesh_optimizer", "status") == "available"

      # Verify entities have required capabilities
      generator_caps = AriaState.get_fact(state, "mesh_generator", "capabilities")
      assert :mesh_creation in generator_caps
      assert :topology_modification in generator_caps

      analyzer_caps = AriaState.get_fact(state, "spatial_analyzer", "capabilities")
      assert :geometry_analysis in analyzer_caps
      assert :constraint_checking in analyzer_caps

      optimizer_caps = AriaState.get_fact(state, "mesh_optimizer", "capabilities")
      assert :mesh_simplification in optimizer_caps
      assert :quality_improvement in optimizer_caps
    end

    test "concurrent mesh operations with entity coordination", %{state: state} do
      # Simulate concurrent mesh operations that would require entity coordination

      # Create multiple meshes
      {:ok, state1} = AriaBmeshDomain.create_bmesh(state, ["mesh_a"])
      {:ok, state2} = AriaBmeshDomain.create_bmesh(state1, ["mesh_b"])
      {:ok, state3} = AriaBmeshDomain.create_bmesh(state2, ["mesh_c"])

      # Verify all meshes exist
      assert AriaState.get_fact(state3, "mesh_a", "mesh_exists") == true
      assert AriaState.get_fact(state3, "mesh_b", "mesh_exists") == true
      assert AriaState.get_fact(state3, "mesh_c", "mesh_exists") == true

      # Perform operations on multiple meshes
      {:ok, state4} = AriaBmeshDomain.modify_topology(state3, ["mesh_a", %{add_vertices: 4}])
      {:ok, state5} = AriaBmeshDomain.modify_topology(state4, ["mesh_b", %{add_vertices: 6}])
      {:ok, final_state} = AriaBmeshDomain.modify_topology(state5, ["mesh_c", %{add_vertices: 8}])

      # Verify final vertex counts
      assert AriaState.get_fact(final_state, "mesh_a", "vertex_count") == 4
      assert AriaState.get_fact(final_state, "mesh_b", "vertex_count") == 6
      assert AriaState.get_fact(final_state, "mesh_c", "vertex_count") == 8
    end

    test "entity capability requirements for complex operations", %{state: state} do
      # Test that complex operations can access required entity capabilities

      # Create a complex mesh that would require multiple capabilities
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["complex_mesh", %{u_segments: 16, v_segments: 12}])

      # This operation would require:
      # - mesh_creation capability (from mesh_generator)
      # - geometry_analysis capability (from spatial_analyzer)
      # - potentially quality_improvement (from mesh_optimizer)

      # Verify entities with required capabilities are available
      generator_available = AriaState.get_fact(state, "mesh_generator", "status") == "available"
      analyzer_available = AriaState.get_fact(state, "spatial_analyzer", "status") == "available"
      optimizer_available = AriaState.get_fact(state, "mesh_optimizer", "status") == "available"

      assert generator_available
      assert analyzer_available
      assert optimizer_available

      # The action sequence should be valid
      assert is_list(actions)
      assert length(actions) > 0
    end
  end

  describe "error handling and recovery workflows" do
    test "mesh creation failure recovery", %{state: state} do
      # Create a mesh first
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["recovery_mesh"])

      # Try to create the same mesh again (should fail)
      {:error, reason} = AriaBmeshDomain.create_bmesh(state_with_mesh, ["recovery_mesh"])
      assert reason == :mesh_already_exists

      # Recovery: Check if mesh exists before creating
      mesh_exists = AriaState.get_fact(state_with_mesh, "recovery_mesh", "mesh_exists")
      if mesh_exists do
        # Mesh already exists, proceed with other operations
        {:ok, final_state} = AriaBmeshDomain.modify_topology(state_with_mesh, ["recovery_mesh", %{add_vertices: 4}])
        assert AriaState.get_fact(final_state, "recovery_mesh", "vertex_count") == 4
      end
    end

    test "vertex operation failure recovery", %{state: state} do
      # Try to add vertex to non-existent mesh
      {:error, reason} = AriaBmeshDomain.add_vertex(state, ["nonexistent_mesh", "v1", {0.0, 0.0, 0.0}])
      assert reason == :mesh_not_found

      # Recovery: Create mesh first, then add vertex
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["recovery_vertex_mesh"])
      {:ok, final_state} = AriaBmeshDomain.add_vertex(state_with_mesh, ["recovery_vertex_mesh", "v1", {0.0, 0.0, 0.0}])

      assert AriaState.get_fact(final_state, {"recovery_vertex_mesh", "v1"}, "vertex_exists") == true
      assert AriaState.get_fact(final_state, "recovery_vertex_mesh", "vertex_count") == 1
    end

    test "face creation failure recovery", %{state: state} do
      # Create mesh but don't add vertices
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["recovery_face_mesh"])

      # Try to create face with non-existent vertices
      {:error, reason} = AriaBmeshDomain.add_face(state_with_mesh, ["recovery_face_mesh", "f1", ["v1", "v2", "v3"]])
      assert reason == :vertices_not_found

      # Recovery: Add vertices first, then create face
      {:ok, state1} = AriaBmeshDomain.add_vertex(state_with_mesh, ["recovery_face_mesh", "v1", {0.0, 0.0, 0.0}])
      {:ok, state2} = AriaBmeshDomain.add_vertex(state1, ["recovery_face_mesh", "v2", {1.0, 0.0, 0.0}])
      {:ok, state3} = AriaBmeshDomain.add_vertex(state2, ["recovery_face_mesh", "v3", {0.0, 1.0, 0.0}])
      {:ok, final_state} = AriaBmeshDomain.add_face(state3, ["recovery_face_mesh", "f1", ["v1", "v2", "v3"]])

      assert AriaState.get_fact(final_state, {"recovery_face_mesh", "f1"}, "face_exists") == true
      assert AriaState.get_fact(final_state, "recovery_face_mesh", "face_count") == 1
    end
  end

  describe "performance and scalability workflows" do
    test "large mesh generation workflow", %{state: state} do
      # Test creating a mesh with many vertices and faces
      params = %{u_segments: 20, v_segments: 15}  # Will generate 300 vertices
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["large_mesh", params])

      # Should handle large action sequences efficiently
      assert length(actions) > 300  # Many actions for large mesh

      # Verify action structure is correct
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)

      assert length(vertex_actions) == 300  # 20 * 15 = 300 vertices
      assert length(face_actions) > 250     # Many faces for high resolution
    end

    test "multiple primitive workflow performance", %{state: state} do
      # Test creating multiple primitives in sequence
      primitives = [
        {:cuboid, %{width: 1.0, height: 1.0, depth: 1.0}},
        {:cylinder, %{radius: 0.5, height: 2.0, radial_segments: 8}},
        {:cone, %{radius: 0.8, height: 1.5, radial_segments: 6}},
        {:pyramid, %{base_width: 1.2, height: 1.8}}
      ]

      # Generate action sequences for all primitives
      all_actions = Enum.with_index(primitives)
      |> Enum.flat_map(fn {{primitive_type, params}, index} ->
        mesh_id = "multi_#{primitive_type}_#{index}"

        case primitive_type do
          :cuboid ->
            {:ok, actions} = Primitives.create_cuboid_task(state, [mesh_id, params])
            actions
          :cylinder ->
            {:ok, actions} = Primitives.create_cylinder_task(state, [mesh_id, params])
            actions
          :cone ->
            {:ok, actions} = Primitives.create_cone_task(state, [mesh_id, params])
            actions
          :pyramid ->
            {:ok, actions} = Primitives.create_pyramid_task(state, [mesh_id, params])
            actions
        end
      end)

      # Should have actions for all primitives
      assert length(all_actions) > 50  # Many actions for multiple primitives

      # Should have create_bmesh actions for each primitive
      create_actions = Enum.filter(all_actions, fn {action, _args} -> action == :create_bmesh end)
      assert length(create_actions) == 4  # One for each primitive
    end

    test "workflow state management efficiency", %{state: state} do
      # Test that state updates are efficient for complex workflows
      start_time = System.monotonic_time(:millisecond)

      # Create and modify multiple meshes
      {:ok, state1} = AriaBmeshDomain.create_bmesh(state, ["perf_mesh_1"])
      {:ok, state2} = AriaBmeshDomain.create_bmesh(state1, ["perf_mesh_2"])
      {:ok, state3} = AriaBmeshDomain.create_bmesh(state2, ["perf_mesh_3"])

      # Add vertices to each mesh
      {:ok, state4} = AriaBmeshDomain.add_vertex(state3, ["perf_mesh_1", "v1", {0.0, 0.0, 0.0}])
      {:ok, state5} = AriaBmeshDomain.add_vertex(state4, ["perf_mesh_2", "v1", {1.0, 0.0, 0.0}])
      {:ok, final_state} = AriaBmeshDomain.add_vertex(state5, ["perf_mesh_3", "v1", {2.0, 0.0, 0.0}])

      end_time = System.monotonic_time(:millisecond)

      # Should complete efficiently
      assert (end_time - start_time) < 1000  # Under 1 second

      # Verify final state
      assert AriaState.get_fact(final_state, "perf_mesh_1", "mesh_exists") == true
      assert AriaState.get_fact(final_state, "perf_mesh_2", "mesh_exists") == true
      assert AriaState.get_fact(final_state, "perf_mesh_3", "mesh_exists") == true
    end
  end

  describe "R25W1398085 workflow compliance validation" do
    test "complete workflow follows specification patterns", %{state: state} do
      # Test a complete workflow that demonstrates R25W1398085 compliance

      # 1. Entity setup (already done in setup)
      assert AriaState.get_fact(state, "mesh_generator", "type") == "generator"

      # 2. Task method decomposition
      {:ok, task_actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["spec_mesh", :medium, :cylinder])

      # 3. Goal achievement
      {:ok, goal_actions} = AriaBmeshDomain.achieve_mesh_existence(state, {"spec_mesh", true})

      # 4. Action execution with proper error handling
      result = case goal_actions do
        [] -> {:ok, state}  # Goal already satisfied
        [action] ->
          case action do
            {:create_bmesh, [mesh_id]} -> AriaBmeshDomain.create_bmesh(state, [mesh_id])
            _ -> {:ok, state}
          end
      end

      assert {:ok, _final_state} = result

      # 5. Verify specification compliance
      assert is_list(task_actions)
      assert length(task_actions) > 0

      # All actions should follow the specification format
      for action <- task_actions do
        case action do
          {action_name, args} when is_atom(action_name) and is_list(args) ->
            assert true  # Proper action format
          {predicate, subject, value} ->
            assert true  # Proper goal format
          _ ->
            flunk("Invalid action format: #{inspect(action)}")
        end
      end
    end
  end
end
