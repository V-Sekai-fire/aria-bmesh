defmodule AriaBmeshDomain.AdvancedPrimitivesTest do
  @moduledoc """
  Tests for advanced geometric primitives following R25W1398085 specification.

  Covers complex primitive generation including ellipsoids, donuts (tori),
  cones, cylinders, and pyramids with comprehensive parameter validation.
  """
  use ExUnit.Case

  alias AriaBmeshDomain
  alias AriaBmeshDomain.Primitives

  setup do
    state = AriaState.new()
    {:ok, state_with_entities} = AriaBmeshDomain.setup_mesh_scenario(state, [])
    {:ok, state: state_with_entities}
  end

  describe "ellipsoid primitive task method" do
    test "creates ellipsoid with default parameters", %{state: state} do
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["ellipsoid_1", %{}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["ellipsoid_1"]} == hd(actions)

      # Should contain vertex and face creation actions
      action_types = Enum.map(actions, fn {action, _args} -> action end)
      assert :add_vertex in action_types
      assert :add_face in action_types

      # Should have reasonable number of vertices for default resolution
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) > 40  # Default u_segments=8, v_segments=6
    end

    test "creates ellipsoid with custom radii", %{state: state} do
      params = %{radius_x: 2.0, radius_y: 1.0, radius_z: 0.5}
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["stretched_ellipsoid", params])

      # Should generate actions with custom parameters
      assert is_list(actions)
      assert {:create_bmesh, ["stretched_ellipsoid"]} == hd(actions)

      # Verify vertex positions reflect custom radii (check a few vertices)
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) > 0

      # Extract some vertex positions to verify scaling
      {_, [_, _, position]} = Enum.at(vertex_actions, 1)
      {x, y, z} = position

      # Positions should be within the ellipsoid bounds
      assert abs(x) <= 2.1  # radius_x with small tolerance
      assert abs(y) <= 1.1  # radius_y with small tolerance
      assert abs(z) <= 0.6  # radius_z with small tolerance
    end

    test "creates ellipsoid with custom resolution", %{state: state} do
      params = %{u_segments: 16, v_segments: 12}
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["hires_ellipsoid", params])

      # Higher resolution should generate more vertices
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) > 150  # 16 * 12 = 192 vertices expected
    end

    test "ellipsoid complexity is high", %{state: _state} do
      assert Primitives.task_complexity(:create_ellipsoid_task) == :high
    end
  end

  describe "donut (torus) primitive task method" do
    test "creates donut with default parameters", %{state: state} do
      {:ok, actions} = Primitives.create_donut_task(state, ["donut_1", %{}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["donut_1"]} == hd(actions)

      # Should contain vertex and face creation actions
      action_types = Enum.map(actions, fn {action, _args} -> action end)
      assert :add_vertex in action_types
      assert :add_face in action_types

      # Should have reasonable number of vertices for torus
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) > 90  # Default major_segments=12, minor_segments=8
    end

    test "creates donut with custom radii", %{state: state} do
      params = %{major_radius: 3.0, minor_radius: 0.8}
      {:ok, actions} = Primitives.create_donut_task(state, ["large_donut", params])

      # Should generate actions with custom parameters
      assert is_list(actions)
      assert {:create_bmesh, ["large_donut"]} == hd(actions)

      # Verify vertex positions reflect custom radii
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      {_, [_, _, position]} = Enum.at(vertex_actions, 1)
      {x, y, z} = position

      # Positions should be within the torus bounds
      # Major radius + minor radius = maximum distance from origin
      distance_from_origin = :math.sqrt(x*x + z*z)
      assert distance_from_origin <= 3.8  # major_radius + minor_radius
      assert abs(y) <= 0.8  # minor_radius
    end

    test "creates donut with custom resolution", %{state: state} do
      params = %{major_segments: 24, minor_segments: 16}
      {:ok, actions} = Primitives.create_donut_task(state, ["hires_donut", params])

      # Higher resolution should generate more vertices
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 384  # 24 * 16 = 384 vertices
    end

    test "donut complexity is high", %{state: _state} do
      assert Primitives.task_complexity(:create_donut_task) == :high
    end
  end

  describe "cone primitive task method" do
    test "creates cone with default parameters", %{state: state} do
      {:ok, actions} = Primitives.create_cone_task(state, ["cone_1", %{}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["cone_1"]} == hd(actions)

      # Should contain vertex and face creation actions
      action_types = Enum.map(actions, fn {action, _args} -> action end)
      assert :add_vertex in action_types
      assert :add_face in action_types

      # Should have vertices for base circle + center + apex
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 10  # 8 radial + 1 center + 1 apex
    end

    test "creates cone with custom dimensions", %{state: state} do
      params = %{radius: 2.0, height: 4.0, radial_segments: 16}
      {:ok, actions} = Primitives.create_cone_task(state, ["large_cone", params])

      # Should generate more vertices with higher resolution
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 18  # 16 radial + 1 center + 1 apex

      # Verify vertex positions reflect custom dimensions
      {_, [_, _, position]} = Enum.at(vertex_actions, 0)
      {x, y, z} = position

      # Base vertices should be at radius distance from center
      if y == -2.0 do  # Bottom vertices (height/2 = 2.0)
        distance_from_center = :math.sqrt(x*x + z*z)
        assert_in_delta distance_from_center, 2.0, 0.1
      end
    end

    test "cone has triangular faces from base to apex", %{state: state} do
      {:ok, actions} = Primitives.create_cone_task(state, ["cone_test", %{radial_segments: 6}])

      # Should have bottom cap faces + side faces
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)
      assert length(face_actions) == 12  # 6 bottom cap + 6 side faces

      # Check that side faces are triangular (3 vertices each)
      side_faces = Enum.drop(face_actions, 6)  # Skip bottom cap faces
      for {_, [_, _, vertices]} <- side_faces do
        assert length(vertices) == 3  # Triangular faces
      end
    end

    test "cone complexity is medium", %{state: _state} do
      assert Primitives.task_complexity(:create_cone_task) == :medium
    end
  end

  describe "cylinder primitive task method" do
    test "creates cylinder with default parameters", %{state: state} do
      {:ok, actions} = Primitives.create_cylinder_task(state, ["cylinder_1", %{}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["cylinder_1"]} == hd(actions)

      # Should contain vertex and face creation actions
      action_types = Enum.map(actions, fn {action, _args} -> action end)
      assert :add_vertex in action_types
      assert :add_face in action_types

      # Should have vertices for top/bottom circles + centers
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 18  # 8 bottom + 8 top + 2 centers
    end

    test "creates cylinder with custom dimensions", %{state: state} do
      params = %{radius: 1.5, height: 3.0, radial_segments: 12}
      {:ok, actions} = Primitives.create_cylinder_task(state, ["custom_cylinder", params])

      # Should generate more vertices with higher resolution
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 26  # 12 bottom + 12 top + 2 centers

      # Verify vertex positions reflect custom dimensions
      bottom_vertices = Enum.filter(vertex_actions, fn {_, [_, vertex_id, {_, y, _}]} ->
        String.contains?(vertex_id, "bottom") and y == -1.5  # height/2
      end)
      assert length(bottom_vertices) == 12
    end

    test "cylinder has proper face structure", %{state: state} do
      {:ok, actions} = Primitives.create_cylinder_task(state, ["cylinder_test", %{radial_segments: 6}])

      # Should have bottom cap + top cap + side faces
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)
      assert length(face_actions) == 18  # 6 bottom + 6 top + 6 side faces

      # Check that side faces are rectangular (4 vertices each)
      side_faces = Enum.drop(face_actions, 12)  # Skip cap faces
      for {_, [_, _, vertices]} <- side_faces do
        assert length(vertices) == 4  # Rectangular faces
      end
    end

    test "cylinder complexity is medium", %{state: _state} do
      assert Primitives.task_complexity(:create_cylinder_task) == :medium
    end
  end

  describe "pyramid primitive task method" do
    test "creates pyramid with default parameters", %{state: state} do
      {:ok, actions} = Primitives.create_pyramid_task(state, ["pyramid_1", %{}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["pyramid_1"]} == hd(actions)

      # Should contain vertex and face creation actions
      action_types = Enum.map(actions, fn {action, _args} -> action end)
      assert :add_vertex in action_types
      assert :add_face in action_types

      # Should have 5 vertices (4 base + 1 apex)
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 5

      # Should have 5 faces (1 base + 4 triangular sides)
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)
      assert length(face_actions) == 5
    end

    test "creates pyramid with custom dimensions", %{state: state} do
      params = %{base_width: 4.0, height: 3.0}
      {:ok, actions} = Primitives.create_pyramid_task(state, ["large_pyramid", params])

      # Should still have 5 vertices and 5 faces
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)

      assert length(vertex_actions) == 5
      assert length(face_actions) == 5

      # Verify vertex positions reflect custom dimensions
      apex_vertex = Enum.find(vertex_actions, fn {_, [_, vertex_id, _]} ->
        vertex_id == "v5"  # Apex vertex
      end)
      {_, [_, _, {x, y, z}]} = apex_vertex

      assert x == 0.0  # Centered
      assert y == 1.5  # height/2
      assert z == 0.0  # Centered
    end

    test "pyramid has proper face structure", %{state: state} do
      {:ok, actions} = Primitives.create_pyramid_task(state, ["pyramid_test", %{}])

      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)

      # Base face should be square (4 vertices)
      {_, [_, _, base_vertices]} = hd(face_actions)
      assert length(base_vertices) == 4

      # Side faces should be triangular (3 vertices each)
      side_faces = tl(face_actions)
      for {_, [_, _, vertices]} <- side_faces do
        assert length(vertices) == 3
      end
    end

    test "pyramid complexity is low", %{state: _state} do
      assert Primitives.task_complexity(:create_pyramid_task) == :low
    end
  end

  describe "triangular prism primitive task method" do
    test "creates triangular prism with default parameters", %{state: state} do
      {:ok, actions} = Primitives.create_triangular_prism_task(state, ["prism_1", %{}])

      # Should return sequence of atomic actions
      assert is_list(actions)
      assert length(actions) > 0

      # First action should be create_bmesh
      assert {:create_bmesh, ["prism_1"]} == hd(actions)

      # Should have 6 vertices (3 front + 3 back)
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 6

      # Should have 8 faces (2 triangular + 3 rectangular)
      face_actions = Enum.filter(actions, fn {action, _args} -> action == :add_face end)
      assert length(face_actions) == 5  # Actually 5 faces in the implementation
    end

    test "creates triangular prism with custom dimensions", %{state: state} do
      params = %{base_width: 3.0, height: 2.5, depth: 1.5}
      {:ok, actions} = Primitives.create_triangular_prism_task(state, ["custom_prism", params])

      # Should still have 6 vertices
      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      assert length(vertex_actions) == 6

      # Verify vertex positions reflect custom dimensions
      {_, [_, _, {x, y, z}]} = hd(vertex_actions)

      # Vertices should be within the prism bounds
      assert abs(x) <= 1.5  # base_width/2
      assert abs(y) <= 1.25  # height/2
      assert abs(z) <= 0.75  # depth/2
    end

    test "triangular prism complexity is low", %{state: _state} do
      assert Primitives.task_complexity(:create_triangular_prism_task) == :low
    end
  end

  describe "primitive task method integration" do
    test "all available task methods can be executed", %{state: state} do
      available_methods = Primitives.available_task_methods()

      for method <- available_methods do
        # Test each method with default parameters
        {:ok, actions} = apply(Primitives, method, [state, ["test_#{method}", %{}]])

        # All should return valid action sequences
        assert is_list(actions)
        assert length(actions) > 0
        assert {:create_bmesh, ["test_#{method}"]} == hd(actions)

        # All should contain vertex and face creation
        action_types = Enum.map(actions, fn {action, _args} -> action end)
        assert :add_vertex in action_types
        assert :add_face in action_types
      end
    end

    test "primitive task methods follow R25W1398085 patterns", %{state: state} do
      # Test that all primitives follow the specification patterns
      {:ok, cuboid_actions} = Primitives.create_cuboid_task(state, ["test_cuboid", %{}])
      {:ok, cylinder_actions} = Primitives.create_cylinder_task(state, ["test_cylinder", %{}])
      {:ok, ellipsoid_actions} = Primitives.create_ellipsoid_task(state, ["test_ellipsoid", %{}])

      # All should start with create_bmesh
      assert {:create_bmesh, ["test_cuboid"]} == hd(cuboid_actions)
      assert {:create_bmesh, ["test_cylinder"]} == hd(cylinder_actions)
      assert {:create_bmesh, ["test_ellipsoid"]} == hd(ellipsoid_actions)

      # All should follow the atomic action pattern
      for actions <- [cuboid_actions, cylinder_actions, ellipsoid_actions] do
        action_types = Enum.map(actions, fn {action, _args} -> action end)
        assert :create_bmesh in action_types
        assert :add_vertex in action_types
        assert :add_face in action_types
      end
    end

    test "complexity distribution follows specification", %{state: _state} do
      available_methods = Primitives.available_task_methods()

      # Count complexity levels
      low_count = Enum.count(available_methods, fn method ->
        Primitives.task_complexity(method) == :low
      end)
      medium_count = Enum.count(available_methods, fn method ->
        Primitives.task_complexity(method) == :medium
      end)
      high_count = Enum.count(available_methods, fn method ->
        Primitives.task_complexity(method) == :high
      end)

      # Should have reasonable distribution
      assert low_count >= 2    # At least cuboid, triangular_prism, pyramid
      assert medium_count >= 2  # At least cylinder, cone
      assert high_count >= 2    # At least ellipsoid, donut

      # Total should match available methods
      assert low_count + medium_count + high_count == length(available_methods)
    end
  end

  describe "parameter validation and edge cases" do
    test "handles zero or negative dimensions gracefully", %{state: state} do
      # Test with zero radius
      {:ok, actions} = Primitives.create_cylinder_task(state, ["zero_cylinder", %{radius: 0.0}])
      assert is_list(actions)
      assert length(actions) > 0

      # Test with very small dimensions
      {:ok, actions} = Primitives.create_cuboid_task(state, ["tiny_cuboid", %{width: 0.001, height: 0.001, depth: 0.001}])
      assert is_list(actions)
      assert length(actions) > 0
    end

    test "handles high resolution parameters", %{state: state} do
      # Test with high resolution ellipsoid
      params = %{u_segments: 32, v_segments: 24}
      {:ok, actions} = Primitives.create_ellipsoid_task(state, ["hires_ellipsoid", params])

      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      # Should generate many vertices (32 * 24 = 768)
      assert length(vertex_actions) > 700
    end

    test "handles minimal resolution parameters", %{state: state} do
      # Test with minimal resolution
      params = %{radial_segments: 3}  # Minimum for a recognizable shape
      {:ok, actions} = Primitives.create_cylinder_task(state, ["minimal_cylinder", params])

      vertex_actions = Enum.filter(actions, fn {action, _args} -> action == :add_vertex end)
      # Should still generate valid geometry
      assert length(vertex_actions) == 8  # 3 bottom + 3 top + 2 centers
    end
  end
end
