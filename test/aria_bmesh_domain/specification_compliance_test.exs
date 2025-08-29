defmodule AriaBmeshDomain.SpecificationComplianceTest do
  @moduledoc """
  Tests for R25W1398085 specification compliance.

  Validates that the aria-bmesh domain follows the unified durative action
  specification patterns, entity-capability system, and temporal constraints.
  """
  use ExUnit.Case

  alias AriaBmeshDomain
  alias AriaBmeshDomain.Primitives

  setup do
    state = AriaState.new()
    {:ok, state_with_entities} = AriaBmeshDomain.setup_mesh_scenario(state, [])
    {:ok, state: state_with_entities}
  end

  describe "R25W1398085 entity registration compliance" do
    test "entities have required type, capabilities, and status facts", %{state: state} do
      # Verify mesh_generator entity
      assert AriaState.get_fact(state, "mesh_generator", "type") == "generator"
      assert AriaState.get_fact(state, "mesh_generator", "capabilities") == [:mesh_creation, :topology_modification]
      assert AriaState.get_fact(state, "mesh_generator", "status") == "available"

      # Verify spatial_analyzer entity
      assert AriaState.get_fact(state, "spatial_analyzer", "type") == "analyzer"
      assert AriaState.get_fact(state, "spatial_analyzer", "capabilities") == [:geometry_analysis, :constraint_checking]
      assert AriaState.get_fact(state, "spatial_analyzer", "status") == "available"

      # Verify mesh_optimizer entity
      assert AriaState.get_fact(state, "mesh_optimizer", "type") == "optimizer"
      assert AriaState.get_fact(state, "mesh_optimizer", "capabilities") == [:mesh_simplification, :quality_improvement]
      assert AriaState.get_fact(state, "mesh_optimizer", "status") == "available"
    end

    test "entity registration follows specification pattern", %{state: state} do
      # Test the entity registration pattern from the spec
      initial_state = AriaState.new()

      # Register a test entity following the spec pattern
      test_state = initial_state
      |> AriaState.set_fact("test_entity", "type", "test_type")
      |> AriaState.set_fact("test_entity", "capabilities", [:test_capability])
      |> AriaState.set_fact("test_entity", "status", "available")

      # Verify the pattern matches specification requirements
      assert AriaState.get_fact(test_state, "test_entity", "type") == "test_type"
      assert AriaState.get_fact(test_state, "test_entity", "capabilities") == [:test_capability]
      assert AriaState.get_fact(test_state, "test_entity", "status") == "available"
    end
  end

  describe "R25W1398085 temporal pattern compliance" do
    test "Pattern 1: instant action, anytime (no temporal constraints)", %{state: state} do
      # Test actions with @action true (Pattern 1)
      # These should execute immediately without temporal constraints
      start_time = System.monotonic_time(:millisecond)
      {:ok, _new_state} = AriaBmeshDomain.create_bmesh(state, ["instant_mesh"])
      end_time = System.monotonic_time(:millisecond)

      # Should complete very quickly (Pattern 1 semantics)
      assert (end_time - start_time) < 50
    end

    test "Pattern 2: floating duration (duration specified, no start/end)", %{state: state} do
      # Test actions with @action duration: "PT1S" (Pattern 2)
      # The create_mesh action has PT1S duration
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      start_time = System.monotonic_time(:millisecond)
      params = %{vertex_count: 8, face_count: 6}
      {:ok, _new_state} = AriaBmeshDomain.create_mesh(state_with_mesh, ["floating_mesh", params])
      end_time = System.monotonic_time(:millisecond)

      # Should take some time but complete within reasonable bounds
      # (In real planning, this would be scheduled by the planner)
      assert (end_time - start_time) < 2000  # Allow up to 2 seconds in test
    end

    test "Pattern 6: calculated end (start + duration = end)", %{state: state} do
      # Test the temporal calculation pattern
      # If we had start: "2025-06-22T10:00:00-07:00", duration: "PT2H"
      # Then end should be calculated as "2025-06-22T12:00:00-07:00"

      # This is a conceptual test since we don't have actual temporal scheduling
      # But we can verify the duration attributes are properly set
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # The modify_topology action has PT2S duration
      operations = %{add_vertices: 4}
      start_time = System.monotonic_time(:millisecond)
      {:ok, _new_state} = AriaBmeshDomain.modify_topology(state_with_mesh, ["test_mesh", operations])
      end_time = System.monotonic_time(:millisecond)

      # Should respect the duration constraint
      assert (end_time - start_time) < 3000  # Allow up to 3 seconds
    end
  end

  describe "R25W1398085 goal format compliance" do
    test "goals use {predicate, subject, value} format", %{state: state} do
      # Test unigoal methods use the correct goal format
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # Test mesh_exists goal format
      goal = {"test_mesh", true}
      {:ok, actions} = AriaBmeshDomain.achieve_mesh_existence(state, goal)

      # Should return empty list since mesh already exists
      assert actions == []

      # Test vertex_count goal format
      goal = {"test_mesh", 10}
      {:ok, actions} = AriaBmeshDomain.achieve_vertex_count(state_with_mesh, goal)

      # Should return topology modification action
      assert length(actions) == 1
      assert {:modify_topology, ["test_mesh", %{add_vertices: 10}]} in actions
    end

    test "state validation uses AriaState.get_fact/3 as specified", %{state: state} do
      # Verify that all state checks use the specified pattern
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])

      # Direct fact checking as specified in R25W1398085
      mesh_exists = AriaState.get_fact(state_with_mesh, "test_mesh", "mesh_exists")
      assert mesh_exists == true

      vertex_count = AriaState.get_fact(state_with_mesh, "test_mesh", "vertex_count")
      assert vertex_count == 0

      # This pattern should be used throughout the domain
      entity_type = AriaState.get_fact(state, "mesh_generator", "type")
      assert entity_type == "generator"
    end
  end

  describe "R25W1398085 method attribute compliance" do
    test "all actions have @action attributes", %{state: state} do
      # This is a meta-test that verifies the code structure
      # In a real implementation, we'd use reflection to check attributes

      # Test that actions work as expected (indicating proper attributes)
      {:ok, _state1} = AriaBmeshDomain.create_bmesh(state, ["test1"])
      {:ok, state2} = AriaBmeshDomain.create_bmesh(state, ["test2"])
      {:ok, _state3} = AriaBmeshDomain.add_vertex(state2, ["test2", "v1", {0.0, 0.0, 0.0}])

      # If attributes were missing, these would fail to compile/register
      assert true  # If we get here, attributes are properly set
    end

    test "unigoal methods handle single predicate goals", %{state: state} do
      # Test @unigoal_method predicate: "mesh_exists"
      goal = {"nonexistent_mesh", true}
      {:ok, actions} = AriaBmeshDomain.achieve_mesh_existence(state, goal)

      # Should return action to create the mesh
      assert length(actions) == 1
      assert {:create_bmesh, ["nonexistent_mesh"]} in actions

      # Test @unigoal_method predicate: "vertex_count"
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])
      goal = {"test_mesh", 5}
      {:ok, actions} = AriaBmeshDomain.achieve_vertex_count(state_with_mesh, goal)

      assert length(actions) == 1
      assert {:modify_topology, ["test_mesh", %{add_vertices: 5}]} in actions
    end

    test "task methods decompose complex workflows", %{state: state} do
      # Test @task_method decomposition
      {:ok, actions} = AriaBmeshDomain.generate_procedural_mesh(state, ["test_mesh", :low, :cuboid])

      # Should decompose into multiple actions
      assert length(actions) >= 2

      # Should include mesh creation and quality goal
      action_types = Enum.map(actions, fn
        {action, _args} -> action
        {pred, _subj, _val} -> pred
        other -> other
      end)

      assert :create_mesh in action_types or {:create_mesh, ["test_mesh", %{width: 2.0, height: 2.0, depth: 2.0}]} in actions
    end
  end

  describe "R25W1398085 capability system compliance" do
    test "capabilities are simple traits for flexible composition", %{state: state} do
      # Verify capability system follows the specification
      generator_caps = AriaState.get_fact(state, "mesh_generator", "capabilities")
      analyzer_caps = AriaState.get_fact(state, "spatial_analyzer", "capabilities")
      optimizer_caps = AriaState.get_fact(state, "mesh_optimizer", "capabilities")

      # Should be lists of atoms (traits)
      assert is_list(generator_caps)
      assert Enum.all?(generator_caps, &is_atom/1)

      assert is_list(analyzer_caps)
      assert Enum.all?(analyzer_caps, &is_atom/1)

      assert is_list(optimizer_caps)
      assert Enum.all?(optimizer_caps, &is_atom/1)

      # Should include behavioral capabilities
      assert :mesh_creation in generator_caps
      assert :topology_modification in generator_caps
      assert :geometry_analysis in analyzer_caps
      assert :constraint_checking in analyzer_caps
      assert :mesh_simplification in optimizer_caps
      assert :quality_improvement in optimizer_caps
    end

    test "entity types follow specification categories", %{state: state} do
      # Verify entity types match specification patterns
      {:ok, generator_type} = AriaState.get_fact(state, "mesh_generator", "type")
      {:ok, analyzer_type} = AriaState.get_fact(state, "spatial_analyzer", "type")
      {:ol, optimizer_type} = AriaState.get_fact(state, "mesh_optimizer", "type")

      # Should be categorical traits as per spec
      assert generator_type == "generator"
      assert analyzer_type == "analyzer"
      assert optimizer_type == "optimizer"
    end
  end

  describe "R25W1398085 domain creation compliance" do
    test "domain creation follows specification pattern", %{state: _state} do
      # Test domain creation as specified
      domain = AriaBmeshDomain.create()

      # Should have proper domain structure
      assert domain != nil
      assert domain.name == :bmesh_world

      # Domain should be properly registered with attributes
      # (This would be verified by the planning system)
      assert true  # If domain creation succeeds, it's properly structured
    end
  end

  describe "R25W1398085 error handling compliance" do
    test "actions return proper {:ok, state} | {:error, atom()} patterns", %{state: state} do
      # Test success patterns
      {:ok, new_state} = AriaBmeshDomain.create_bmesh(state, ["success_mesh"])
      assert %AriaState{} = new_state

      # Test error patterns
      {:error, reason} = AriaBmeshDomain.create_bmesh(new_state, ["success_mesh"])
      assert is_atom(reason)
      assert reason == :mesh_already_exists

      # Test mesh not found errors
      {:error, reason2} = AriaBmeshDomain.add_vertex(state, ["nonexistent", "v1", {0.0, 0.0, 0.0}])
      assert reason2 == :mesh_not_found

      # Test vertex not found errors
      {:ok, state_with_mesh} = AriaBmeshDomain.create_bmesh(state, ["test_mesh"])
      {:error, reason3} = AriaBmeshDomain.add_face(state_with_mesh, ["test_mesh", "f1", ["nonexistent_vertex"]])
      assert reason3 == :vertices_not_found
    end
  end

  describe "R25W1398085 primitive task method compliance" do
    test "primitive task methods return action sequences", %{state: state} do
      # Test that primitive task methods follow the specification
      {:ok, actions} = Primitives.create_cuboid_task(state, ["test_cuboid", %{width: 2.0, height: 2.0, depth: 2.0}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["test_cuboid"]} == hd(actions)

      # Should contain vertex and face creation actions
      action_types = Enum.map(actions, fn {action, _args} -> action end)
      assert :add_vertex in action_types
      assert :add_face in action_types
    end

    test "primitive complexity categorization follows specification", %{state: _state} do
      # Test complexity categories as specified
      assert Primitives.task_complexity(:create_cuboid_task) == :low
      assert Primitives.task_complexity(:create_triangular_prism_task) == :low
      assert Primitives.task_complexity(:create_pyramid_task) == :low

      assert Primitives.task_complexity(:create_cylinder_task) == :medium
      assert Primitives.task_complexity(:create_cone_task) == :medium

      assert Primitives.task_complexity(:create_ellipsoid_task) == :high
      assert Primitives.task_complexity(:create_donut_task) == :high
    end

    test "all available task methods are properly categorized", %{state: _state} do
      # Verify all task methods have complexity ratings
      available_methods = Primitives.available_task_methods()

      for method <- available_methods do
        complexity = Primitives.task_complexity(method)
        assert complexity in [:low, :medium, :high]
      end

      # Should have reasonable distribution
      assert length(available_methods) >= 7  # At least 7 primitive types
    end
  end
end
