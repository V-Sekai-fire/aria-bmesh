# AriaBmesh

Topological mesh data structures for n-gon geometry in Elixir.

## Overview

AriaBmesh provides a complete BMesh implementation for representing 3D meshes with support for:
- **N-gon faces**: Triangles, quads, and polygons with any number of vertices
- **Non-manifold geometry**: Edges can connect multiple faces
- **Topological navigation**: Efficient traversal of mesh connectivity
- **Per-corner attributes**: UV coordinates, colors, and other attributes stored on face corners (loops)

## Features

- **Vertices**: 3D positions with edge connections and attributes
- **Edges**: Connect two vertices, support multiple faces (non-manifold)
- **Loops**: Face corners with navigation pointers for boundary and radial traversal
- **Faces**: N-gon polygons with vertices, edges, loops, and attributes
- **Topology**: Navigation functions for traversing mesh connectivity

## Installation

Add `aria_bmesh` to your list of dependencies in `mix.exs`:

```elixir
def deps do
  [
    {:aria_bmesh, git: "https://github.com/V-Sekai-fire/aria-bmesh.git"}
  ]
end
```

## Usage

### Creating a Mesh

```elixir
# Create an empty mesh
mesh = AriaBmesh.Mesh.new()

# Add vertices
{mesh, v1} = AriaBmesh.Mesh.add_vertex(mesh, {0.0, 0.0, 0.0})
{mesh, v2} = AriaBmesh.Mesh.add_vertex(mesh, {1.0, 0.0, 0.0})
{mesh, v3} = AriaBmesh.Mesh.add_vertex(mesh, {0.0, 1.0, 0.0})

# Add edges
{mesh, e1} = AriaBmesh.Mesh.add_edge(mesh, {v1, v2})
{mesh, e2} = AriaBmesh.Mesh.add_edge(mesh, {v2, v3})
{mesh, e3} = AriaBmesh.Mesh.add_edge(mesh, {v3, v1})

# Add a face (triangle)
{mesh, face_id} = AriaBmesh.Mesh.add_face(mesh, [v1, v2, v3])
```

### Working with Attributes

```elixir
# Add vertex attributes
vertex = AriaBmesh.Vertex.new(0, {1.0, 2.0, 3.0})
vertex = AriaBmesh.Vertex.set_attribute(vertex, "NORMAL", {0.0, 1.0, 0.0})

# Add loop attributes (per-corner UVs)
loop = AriaBmesh.Loop.new(0, vertex_id, edge_id, face_id)
loop = AriaBmesh.Loop.set_attribute(loop, "TEXCOORD_0", {0.5, 0.5})
```

### Topological Navigation

```elixir
# Get all faces sharing an edge (non-manifold support)
edge = AriaBmesh.Mesh.get_edge(mesh, edge_id)
faces = AriaBmesh.Topology.edge_faces(mesh, edge)

# Get all loops in a face boundary (in order)
face = AriaBmesh.Mesh.get_face(mesh, face_id)
loops = AriaBmesh.Topology.face_loops(mesh, face)

# Check if edge is manifold
is_manifold = AriaBmesh.Topology.edge_manifold?(mesh, edge)
```

## Core Modules

- `AriaBmesh.Mesh` - Container for vertices, edges, loops, and faces
- `AriaBmesh.Vertex` - Vertex structure with position and attributes
- `AriaBmesh.Edge` - Edge structure connecting two vertices
- `AriaBmesh.Loop` - Face corner with navigation pointers
- `AriaBmesh.Face` - N-gon face structure
- `AriaBmesh.Topology` - Topological navigation functions

## Requirements

- Elixir ~> 1.18

## License

MIT
