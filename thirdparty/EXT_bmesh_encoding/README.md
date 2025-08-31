# EXT_bmesh_encoding

## Contributors

- K. S. Ernest (iFire) Lee, Individual Contributor / https://github.com/fire
- Based on principles from FB_ngon_encoding by Pär Winzell and Michael Bunnell (Facebook)

## Status

Active Development

## Dependencies

Written against the glTF 2.0 spec, superseding FB_ngon_encoding.
Compatible with EXT_mesh_manifold for manifold topology validation.

## References

The BMesh data structure is described in:

- Gueorguieva, Stefka and Marcheix, Davi. 1994. "Non-manifold boundary representation for solid modeling."
- BMeshUnity implementation: https://github.com/eliemichel/BMeshUnity.git

## Overview

While glTF can only deliver a polygon mesh after it's been decomposed into triangles, there are cases where access to the full BMesh topology is still useful. BMesh provides a non-manifold boundary representation with vertices, edges, loops, and faces that enables complex geometric operations.

This extension provides a **hybrid encoding scheme** that combines:

1. **Implicit triangle fan encoding** (like FB_ngon_encoding) as the baseline for glTF 2.0 compatibility
2. **Explicit BMesh topology data** that provides complete BMesh reconstruction when supported

This approach ensures graceful degradation: files work in any glTF 2.0 viewer with basic polygon support, while providing rich BMesh features when the extension is fully supported.

## Key Features

### Hybrid Encoding Approach

- **Implicit Base Layer**: Triangle fan ordering (FB_ngon_encoding compatible) ensures glTF 2.0 compatibility
- **Explicit Enhancement Layer**: Complete BMesh topology data for full reconstruction
- **Graceful Degradation**: Works in any glTF 2.0 viewer, enhanced features when extension supported
- **Non-manifold Support**: Full support for non-manifold edges and vertices
- **Required Implementation**: All implementations must support both implicit and explicit layers

## Extension Structure

**Small Meshes** (JSON format):

```json
{
  "meshes": [
    {
      "name": "BMeshModel",
      "primitives": [
        {
          "indices": 0,
          "attributes": {
            "POSITION": 1,
            "NORMAL": 2,
            "TEXCOORD_0": 3
          },
          "material": 0,
          "mode": 4,
          "extensions": {
            "EXT_bmesh_encoding": {
              "vertices": [
                {
                  "id": 0,
                  "position": [0.0, 0.0, 0.0],
                  "edges": [0, 1],
                  "attributes": { "weight": 0.5 }
                }
              ],
              "edges": [
                {
                  "id": 0,
                  "vertices": [0, 1],
                  "faces": [0],
                  "manifold": true,
                  "attributes": { "crease": 0.0 }
                }
              ],
              "loops": [
                {
                  "id": 0,
                  "vertex": 0,
                  "edge": 0,
                  "face": 0,
                  "next": 1,
                  "prev": 2,
                  "radial_next": 0,
                  "radial_prev": 0,
                  "attributes": { "TEXCOORD_0": [0.0, 0.0] }
                }
              ],
              "faces": [
                {
                  "id": 0,
                  "vertices": [0, 1, 2],
                  "edges": [0, 1, 2],
                  "loops": [0, 1, 2],
                  "normal": [0.0, 0.0, 1.0],
                  "materialIndex": 1
                }
              ]
            }
          }
        }
      ]
    }
  ]
}
```

**Large Meshes** (glTF buffer format):

```json
{
  "meshes": [
    {
      "name": "LargeBMeshModel",
      "primitives": [
        {
          "indices": 0,
          "attributes": {
            "POSITION": 1,
            "NORMAL": 2,
            "TEXCOORD_0": 3
          },
          "material": 0,
          "mode": 4,
          "extensions": {
            "EXT_bmesh_encoding": {
              "vertices": {
                "count": 10000,
                "positions": 10,
                "edges": 11,
                "attributes": {
                  "weight": 12
                }
              },
              "edges": {
                "count": 15000,
                "vertices": 13,
                "faces": 14,
                "manifold": 15
              },
              "loops": {
                "count": 20000,
                "topology": 16,
                "attributes": {
                  "uv": 17
                }
              },
              "faces": {
                "count": 5000,
                "vertices": 18,
                "edges": 19,
                "loops": 20,
                "offsets": 21,
                "normals": 22
              }
            }
          }
        }
      ]
    }
  ]
}
```

## Implicit Triangle Fan Algorithm

Building on FB_ngon_encoding principles with BMesh enhancements:

### Core Principle

Like FB_ngon_encoding, the **order of triangles and per-triangle vertex indices** holds all information needed to reconstruct BMesh topology. The algorithm uses an enhanced triangulation process:

- For each BMesh face `f`, choose one identifying vertex `v(f)`
- Break the face into a triangle fan, all anchored at `v(f)`
- Ensure `v(f) != v(f')` for consecutive faces
- Use enhanced vertex selection for optimal BMesh reconstruction

### Encoding Process (Implicit Only)

1. **BMesh Face Analysis**: Analyze BMesh faces for optimal triangulation
2. **Enhanced Anchor Selection**: Choose anchor vertex to minimize reconstruction ambiguity
3. **Triangle Fan Generation**: Create triangle fans with optimal vertex ordering
4. **Standard glTF Output**: Produce standard glTF triangles with no additional data

### Reconstruction Process

1. **Triangle Grouping**: Group consecutive triangles sharing the same `triangle.vertices[0]`
2. **BMesh Face Rebuilding**: Reconstruct BMesh faces from triangle fans
3. **Topology Inference**: Infer BMesh edge and loop structure from face connectivity
4. **Validation**: Validate reconstructed BMesh for topological consistency

## Bidirectional Conversion

### BMesh → glTF (Encoding)

```javascript
// Convert complete BMesh to glTF with hybrid encoding
const gltfData = encodeBmeshToGltf(bmesh);

// Produces:
// 1. Standard glTF triangle mesh (implicit triangle fans)
// 2. Extension data with complete BMesh topology (vertices, edges, loops, faces)
// 3. Attributes preserved for all BMesh elements
```

### glTF → BMesh (Decoding)

```javascript
// Full BMesh reconstruction when extension is supported
const completeBmesh = decodeBmeshFromGltf(gltfData);

// Includes:
// - All vertices with positions and attributes
// - All edges with adjacency and manifold flags
// - All loops with navigation and attributes (UVs, colors)
// - All faces with boundaries and attributes
// - Complete topological relationships

// Graceful degradation when extension unsupported
const polygons = decodeBmeshImplicit(gltfTriangles);
// Produces basic polygon list from triangle fan reconstruction
```

## Implementation Requirements

All EXT_bmesh_encoding implementations must support:

1. **Hybrid Encoding**: Both implicit triangle fan and explicit BMesh topology data
2. **glTF 2.0 Compatibility**: Files work in any glTF 2.0 viewer via triangle fan fallback
3. **Full BMesh Reconstruction**: Complete topology, attributes, and non-manifold support when extension is recognized
4. **Graceful Degradation**: Automatic fallback to polygon reconstruction when extension unsupported

### Implementation Guidance

**Simple Writers** (minimal implementation):

- Use `manifold: null` for all edges (no manifold checking required)
- Store basic BMesh topology without complex validation
- Focus on core encoding functionality

**Advanced Writers** (full implementation):

- Perform manifold checking and set appropriate `manifold` values
- Validate topology during encoding
- Optimize for specific use cases (CAD, gaming, etc.)

**Readers** (all implementations):

- Treat `manifold: null` as potentially non-manifold for safety
- Handle all three manifold states gracefully
- Provide fallback behavior for unknown manifold status

## Advantages over FB_ngon_encoding

1. **BMesh Optimized**: Enhanced reconstruction specifically for BMesh structures
2. **Better Anchor Selection**: Improved vertex selection algorithm for complex polygons
3. **Robust Reconstruction**: Enhanced handling of edge cases in triangle fan reconstruction
4. **BMesh Topology**: Automatic inference of BMesh edge and loop structures
5. **Backward Compatible**: Falls back gracefully to FB_ngon_encoding behavior
6. **Zero Overhead**: No additional data beyond standard glTF triangles

## Algorithm Details

### Enhanced Triangle Fan Encoding

```javascript
// Implicit encoding - no additional data stored
function encodeBmeshImplicit(bmeshFaces) {
  const triangles = [];
  let prevAnchor = -1; // invalid vertex index

  for (const face of bmeshFaces) {
    // Select anchor: use smallest vertex index different from previous anchor
    const vertices = face.vertices;
    const candidates = vertices.filter((v) => v !== prevAnchor);
    const anchor =
      candidates.length > 0 ? Math.min(...candidates) : vertices[0];
    prevAnchor = anchor;

    const n = vertices.length;
    const anchorIdx = vertices.indexOf(anchor);

    // Create triangle fan from anchor
    for (let i = 2; i < n; i++) {
      const v1Idx = (anchorIdx + i - 1) % n;
      const v2Idx = (anchorIdx + i) % n;
      const triangle = [anchor, vertices[v1Idx], vertices[v2Idx]];
      triangles.push(triangle);
    }
  }

  return triangles;
}

// BMesh-enhanced reconstruction
function decodeBmeshImplicit(triangles) {
  const bmeshFaces = [];
  let currentFaceTriangles = [];
  let prevAnchor = -1;

  for (const triangle of triangles) {
    const anchor = triangle[0];

    if (anchor !== prevAnchor) {
      if (currentFaceTriangles.length > 0) {
        // Extract vertices from triangle fan and create face
        const vertices = extractVerticesFromTriangleFan(currentFaceTriangles);
        bmeshFaces.push({ vertices: vertices });
      }
      currentFaceTriangles = [triangle];
      prevAnchor = anchor;
    } else {
      currentFaceTriangles.push(triangle);
    }
  }

  // Handle last face
  if (currentFaceTriangles.length > 0) {
    const vertices = extractVerticesFromTriangleFan(currentFaceTriangles);
    bmeshFaces.push({ vertices: vertices });
  }

  return bmeshFaces;
}

function extractVerticesFromTriangleFan(triangles) {
  if (triangles.length === 1) {
    return triangles[0]; // Single triangle
  }

  // Rebuild polygon from triangle fan
  const anchor = triangles[0][0];
  const vertices = [anchor];
  const used = new Set([anchor]);

  for (const triangle of triangles) {
    for (let i = 1; i < triangle.length; i++) {
      if (!used.has(triangle[i])) {
        vertices.push(triangle[i]);
        used.add(triangle[i]);
      }
    }
  }

  return vertices;
}

// Complete BMesh reconstruction from explicit data
function reconstructCompleteBMesh(gltfData) {
  const bmesh = {
    vertices: new Map(),
    edges: new Map(),
    loops: new Map(),
    faces: new Map(),
  };

  const extension = gltfData.extensions.EXT_bmesh_encoding;

  // Reconstruct vertices
  for (const vertexData of extension.vertices) {
    bmesh.vertices.set(vertexData.id, {
      id: vertexData.id,
      position: vertexData.position,
      edges: [],
      attributes: vertexData.attributes || {},
    });
  }

  // Reconstruct edges
  for (const edgeData of extension.edges) {
    const edge = {
      id: edgeData.id,
      vertices: edgeData.vertices,
      faces: [],
      manifold: edgeData.manifold,
      attributes: edgeData.attributes || {},
    };
    bmesh.edges.set(edgeData.id, edge);

    // Link vertices to edges
    for (const vertexId of edgeData.vertices) {
      bmesh.vertices.get(vertexId).edges.push(edgeData.id);
    }
  }

  // Reconstruct loops with navigation
  for (const loopData of extension.loops) {
    bmesh.loops.set(loopData.id, {
      id: loopData.id,
      vertex: loopData.vertex,
      edge: loopData.edge,
      face: loopData.face,
      next: loopData.next,
      prev: loopData.prev,
      radial_next: loopData.radial_next,
      radial_prev: loopData.radial_prev,
      attributes: loopData.attributes || {},
    });
  }

  // Reconstruct faces
  for (const faceData of extension.faces) {
    const face = {
      id: faceData.id,
      vertices: faceData.vertices,
      edges: faceData.edges || [],
      loops: faceData.loops || [],
      normal: faceData.normal,
      attributes: faceData.attributes || {},
    };
    bmesh.faces.set(faceData.id, face);

    // Link edges to faces
    for (const edgeId of face.edges) {
      bmesh.edges.get(edgeId).faces.push(faceData.id);
    }
  }

  return bmesh;
}
```

## glTF Schema Updates

- **JSON schema**: [glTF.EXT_bmesh_encoding.schema.json](schema/glTF.EXT_bmesh_encoding.schema.json)

## Implementation Status

- [x] Core implicit encoding specification design
- [x] Enhanced triangle fan algorithm design

## Known Implementations

- Aria BMesh Domain (Elixir) - In Development

## BMesh Data Structures

The following BMesh structures are preserved through the implicit encoding:

### Vertex

- **Position**: 3D coordinates (x, y, z)
- **Connected Edges**: List of edges using this vertex
- **Attributes**: Custom vertex data (weights, colors, etc.)

### Edge

- **Vertices**: Two vertex references (start, end)
- **Adjacent Faces**: List of faces sharing this edge
- **Manifold Status**: Three-state flag compatible with EXT_mesh_manifold
  - `true`: Confirmed manifold (oriented 2-manifold with matching halfedges)
  - `false`: Confirmed non-manifold
  - `null`: Unknown status (no manifold checking performed)
- **Attributes**: Custom edge data (creases, weights, etc.)

### Loop

- **Vertex**: Corner vertex reference
- **Edge**: Outgoing edge from vertex
- **Face**: Containing face reference
- **Navigation**: Next/previous loop in face, radial next/previous around edge
- **Attributes**: Per-corner data (UVs, vertex colors, normals)

### Face

- **Vertices**: Ordered vertex sequence defining polygon
- **Edges**: Boundary edges forming face perimeter
- **Loops**: Corner loops (one per vertex)
- **Normal**: Face normal vector
- **Attributes**: Custom face data (material IDs, smoothing groups)

### Topological Relationships

- **Vertex-Edge**: One-to-many (vertex connects to multiple edges)
- **Edge-Face**: One-to-many (edge shared by multiple faces, enables non-manifold)
- **Face-Loop**: One-to-many (face has loops for each corner)
- **Loop Navigation**: Circular lists around faces and radially around edges

## Binary Buffer Layouts

For large meshes, BMesh topology data is stored in glTF buffers using the following binary layouts:

### Vertex Buffers

- **positions**: `Vec3<f32>` (12 bytes per vertex) - 3D coordinates
- **edges**: Variable-length edge lists with offset indexing
- **attributes**: Typed attribute data per vertex

### Edge Buffers

- **vertices**: `[u32, u32]` (8 bytes per edge) - vertex index pairs
- **faces**: Variable-length face lists with offset indexing
- **manifold**: `u8` (1 byte per edge) - manifold status flag
- **attributes**: Typed attribute data per edge

### Loop Buffers

- **topology**: `[u32; 7]` (28 bytes per loop) - vertex, edge, face, next, prev, radial_next, radial_prev indices
- **attributes**: Typed attribute data per loop (UVs, colors, etc.)

### Face Buffers

- **vertices**: Variable-length vertex index lists
- **edges**: Variable-length edge index lists
- **loops**: Variable-length loop index lists
- **offsets**: `[u32; 3]` (12 bytes per face) - start offsets for vertices, edges, loops arrays
- **normals**: `Vec3<f32>` (12 bytes per face) - face normal vectors
- **attributes**: Typed attribute data per face

### Variable-Length Array Encoding

For arrays with variable length (face vertices, edges, loops), data is stored as:

1. **Packed Data Buffer**: Concatenated array elements
2. **Offset Buffer**: Start indices for each element's data
3. **Access Pattern**: `data[offsets[i]:offsets[i+1]]` gives element i's array

### Oriented 2-Manifold Validation

EXT_bmesh_encoding supports EXT_mesh_manifold compatibility through BMesh topology validation:

- **Halfedge Matching**: Each edge's loops provide halfedge information for manifold validation
- **Radial Navigation**: Loop radial_next/radial_prev enable halfedge pair detection
- **Manifold Flagging**: Edge manifold flags indicate EXT_mesh_manifold compliance
- **Topology Validation**: BMesh loop structure allows verification of oriented 2-manifold properties
