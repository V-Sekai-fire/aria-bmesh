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

This extension provides **buffer-based BMesh encoding** that stores complete topology information in glTF buffers for optimal performance while maintaining full glTF 2.0 compatibility.

## Key Features

### Buffer-Based Storage

- **High Performance**: All BMesh data stored in binary buffers for optimal memory usage
- **glTF 2.0 Compliance**: Follows standard glTF buffer view and accessor patterns
- **Scalable**: Efficient for meshes of any size
- **Standard Attributes**: Uses glTF 2.0 attribute naming conventions (TEXCOORD_0, etc.)
- **Non-manifold Support**: Complete support for non-manifold edges and vertices

## Extension Structure

glTF buffer format (all data stored in buffer views):

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
              "vertices": {
                "count": 10000,
                "positions": 10,
                "edges": 11,
                "attributes": {
                  "_WEIGHT": 12
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
                  "TEXCOORD_0": 17
                }
              },
              "faces": {
                "count": 5000,
                "vertices": 18,
                "edges": 19,
                "loops": 20,
                "offsets": 21,
                "normals": 22,
                "materials": 23
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
- **Ensure `v(f) != v(f')` for consecutive faces** (mandatory requirement for unambiguous reconstruction)
- Use enhanced vertex selection for optimal BMesh reconstruction

### Encoding Process (Implicit Layer)

1. **BMesh Face Analysis**: Analyze BMesh faces for optimal triangulation
2. **Enhanced Anchor Selection**: Choose anchor vertex to minimize reconstruction ambiguity
3. **Triangle Fan Generation**: Create triangle fans with optimal vertex ordering
4. **Standard glTF Output**: Produce standard glTF triangles following triangle fan pattern

### Reconstruction Process

1. **Triangle Grouping**: Group consecutive triangles sharing the same `triangle.vertices[0]`
2. **BMesh Face Rebuilding**: Reconstruct BMesh faces from triangle fans
3. **Topology Inference**: Infer BMesh edge and loop structure from face connectivity
4. **Validation**: Validate reconstructed BMesh for topological consistency

## Buffer-Based Encoding (Explicit Layer)

### BMesh → glTF (Encoding)

```javascript
// Convert complete BMesh to glTF with buffer-based encoding
const gltfData = encodeBmeshToGltf(bmesh);

// Produces:
// 1. Standard glTF triangle mesh (implicit triangle fans)
// 2. Extension data with complete BMesh topology in buffers
// 3. All attributes preserved using glTF 2.0 naming conventions
```

### glTF → BMesh (Decoding)

```javascript
// Full BMesh reconstruction from buffer data
const completeBmesh = decodeBmeshFromBuffers(gltfData);

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

## Buffer Layouts

All BMesh topology data is stored in glTF buffers using efficient binary layouts:

### Vertex Buffers

- **positions**: `Vec3<f32>` (12 bytes per vertex) - 3D coordinates
- **edges**: Variable-length edge lists with offset indexing
- **attributes**: Standard glTF attributes (POSITION, NORMAL, TEXCOORD_0, etc.)

### Edge Buffers

- **vertices**: `[u32, u32]` (8 bytes per edge) - vertex index pairs
- **faces**: Variable-length face lists with offset indexing
- **manifold**: `u8` (1 byte per edge) - manifold status flag
  - `0`: Confirmed non-manifold
  - `1`: Confirmed manifold 
  - `255`: Unknown status
- **attributes**: Custom edge data with `_` prefix naming

### Loop Buffers

- **topology**: `[u32; 7]` (28 bytes per loop) - vertex, edge, face, next, prev, radial_next, radial_prev indices
- **attributes**: glTF 2.0 compliant attributes (TEXCOORD_0, COLOR_0, etc.)

### Face Buffers

- **vertices**: Variable-length vertex index lists
- **edges**: Variable-length edge index lists  
- **loops**: Variable-length loop index lists
- **offsets**: `[u32; 3]` (12 bytes per face) - start offsets for vertices, edges, loops arrays
- **normals**: `Vec3<f32>` (12 bytes per face) - face normal vectors
- **attributes**: Custom face data with `_` prefix naming

### Variable-Length Array Encoding

For arrays with variable length (face vertices, edges, loops), data is stored as:

1. **Packed Data Buffer**: Concatenated array elements
2. **Offset Buffer**: Start indices for each element's data  
3. **Access Pattern**: `data[offsets[i]:offsets[i+1]]` gives element i's array

## Implementation Requirements

All EXT_bmesh_encoding implementations must support:

1. **Buffer-Based Storage**: All topology data in glTF buffers for performance
2. **glTF 2.0 Compliance**: Standard buffer views, accessors, and attribute naming
3. **Triangle Fan Compatibility**: Maintains FB_ngon_encoding reconstruction principles
4. **Complete Topology**: Full BMesh reconstruction with vertices, edges, loops, faces
5. **Graceful Degradation**: Automatic fallback to triangle fan reconstruction when extension unsupported

### Implementation Guidance

**Simple Writers** (minimal implementation):

- Use `manifold: 255` for all edges (no manifold checking required)
- Store basic BMesh topology without complex validation
- Focus on core buffer encoding functionality

**Advanced Writers** (full implementation):

- Perform manifold checking and set appropriate manifold values (0, 1, 255)
- Validate topology during encoding
- Optimize buffer layouts for specific use cases

**Readers** (all implementations):

- Handle all three manifold states gracefully
- Provide fallback behavior for unknown manifold status
- Support reconstruction from either implicit triangles or explicit buffers

## Advantages over FB_ngon_encoding

1. **Complete Topology**: Full BMesh structure with edges and loops, not just faces
2. **Performance Optimized**: Binary buffer storage instead of JSON arrays
3. **Non-manifold Support**: Explicit handling of non-manifold geometry
4. **Attribute Rich**: Comprehensive attribute support at all topology levels
5. **glTF 2.0 Native**: Follows glTF buffer patterns and naming conventions
6. **Backward Compatible**: Falls back gracefully to triangle fan reconstruction

## Algorithm Details

### Enhanced Triangle Fan Encoding

```javascript
// Implicit encoding - maintains triangle fan pattern for compatibility
function encodeBmeshImplicit(bmeshFaces) {
  const triangles = [];
  let prevAnchor = -1;

  for (const face of bmeshFaces) {
    const vertices = face.vertices;
    // Select anchor: use smallest vertex index different from previous anchor
    const candidates = vertices.filter((v) => v !== prevAnchor);
    const anchor = candidates.length > 0 ? Math.min(...candidates) : vertices[0];
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

// Buffer-based BMesh reconstruction
function decodeBmeshFromBuffers(gltfData) {
  const bmesh = {
    vertices: new Map(),
    edges: new Map(), 
    loops: new Map(),
    faces: new Map(),
  };

  const ext = gltfData.extensions.EXT_bmesh_encoding;
  const buffers = gltfData.buffers;
  const bufferViews = gltfData.bufferViews;

  // Reconstruct vertices from buffer data
  const vertexPositions = readBufferView(buffers, bufferViews, ext.vertices.positions);
  for (let i = 0; i < ext.vertices.count; i++) {
    bmesh.vertices.set(i, {
      id: i,
      position: [vertexPositions[i*3], vertexPositions[i*3+1], vertexPositions[i*3+2]],
      edges: [],
      attributes: {},
    });
  }

  // Reconstruct edges from buffer data
  const edgeVertices = readBufferView(buffers, bufferViews, ext.edges.vertices);
  const manifoldFlags = readBufferView(buffers, bufferViews, ext.edges.manifold);
  
  for (let i = 0; i < ext.edges.count; i++) {
    const edge = {
      id: i,
      vertices: [edgeVertices[i*2], edgeVertices[i*2+1]],
      faces: [],
      manifold: manifoldFlags[i] === 1 ? true : (manifoldFlags[i] === 0 ? false : null),
      attributes: {},
    };
    bmesh.edges.set(i, edge);
  }

  // Reconstruct loops from buffer data  
  const loopTopology = readBufferView(buffers, bufferViews, ext.loops.topology);
  
  for (let i = 0; i < ext.loops.count; i++) {
    bmesh.loops.set(i, {
      id: i,
      vertex: loopTopology[i*7],
      edge: loopTopology[i*7+1], 
      face: loopTopology[i*7+2],
      next: loopTopology[i*7+3],
      prev: loopTopology[i*7+4],
      radial_next: loopTopology[i*7+5],
      radial_prev: loopTopology[i*7+6],
      attributes: {},
    });
  }

  // Reconstruct faces from buffer data
  const faceVertices = readBufferView(buffers, bufferViews, ext.faces.vertices);
  const faceOffsets = readBufferView(buffers, bufferViews, ext.faces.offsets);
  const faceNormals = readBufferView(buffers, bufferViews, ext.faces.normals);
  
  for (let i = 0; i < ext.faces.count; i++) {
    const vertexStart = faceOffsets[i*3];
    const vertexEnd = faceOffsets[i*3+1];
    
    const face = {
      id: i,
      vertices: faceVertices.slice(vertexStart, vertexEnd),
      edges: [],
      loops: [],
      normal: [faceNormals[i*3], faceNormals[i*3+1], faceNormals[i*3+2]],
      attributes: {},
    };
    bmesh.faces.set(i, face);
  }

  return bmesh;
}

function readBufferView(buffers, bufferViews, bufferViewIndex) {
  const bufferView = bufferViews[bufferViewIndex];
  const buffer = buffers[bufferView.buffer];
  return new Uint32Array(buffer, bufferView.byteOffset, bufferView.byteLength / 4);
}
```

## glTF Schema

- **JSON schema**: [glTF.EXT_bmesh_encoding.schema.json](schema/glTF.EXT_bmesh_encoding.schema.json)

## Implementation Status

- [x] Core buffer-based encoding specification
- [x] Enhanced triangle fan algorithm design  
- [x] Complete glTF 2.0 buffer integration

## Known Implementations

- Aria BMesh Domain (Elixir) - In Development
- VRM Add-on for Blender (Python) - Active Development

## BMesh Data Structures

The following BMesh structures are preserved through buffer-based encoding:

### Vertex

- **Position**: 3D coordinates (x, y, z) stored in `positions` buffer view
- **Connected Edges**: Edge adjacency data in variable-length format
- **Attributes**: Standard glTF attributes (POSITION, NORMAL, TEXCOORD_0, etc.)

### Edge  

- **Vertices**: Two vertex references stored as `[u32, u32]` pairs
- **Adjacent Faces**: Variable-length face lists with offset indexing
- **Manifold Status**: Single byte flag compatible with EXT_mesh_manifold
  - `0`: Confirmed non-manifold
  - `1`: Confirmed manifold (oriented 2-manifold) 
  - `255`: Unknown status (no manifold checking performed)
- **Attributes**: Custom edge data with `_` prefix naming

### Loop

- **Vertex**: Corner vertex reference
- **Edge**: Outgoing edge from vertex  
- **Face**: Containing face reference
- **Navigation**: Next/previous loop in face, radial next/previous around edge
- **Topology**: All navigation stored as 7×u32 array per loop
- **Attributes**: Per-corner data using glTF naming (TEXCOORD_0, COLOR_0, etc.)

### Face

- **Vertices**: Variable-length vertex index lists with offset indexing
- **Edges**: Variable-length edge index lists with offset indexing  
- **Loops**: Variable-length loop index lists with offset indexing
- **Normal**: Face normal vector stored as Vec3<f32>
- **Attributes**: Custom face data with `_` prefix naming

### Topological Relationships

- **Vertex-Edge**: One-to-many (vertex connects to multiple edges)
- **Edge-Face**: One-to-many (edge shared by multiple faces, enables non-manifold)  
- **Face-Loop**: One-to-many (face has loops for each corner)
- **Loop Navigation**: Circular lists around faces and radially around edges

## Buffer Storage Patterns

### Fixed-Size Data

Data with known size per element (positions, normals, topology):

```
Buffer Layout: [elem0][elem1][elem2]...[elemN]
Access: element[i] = buffer[i * elementSize : (i+1) * elementSize]
```

### Variable-Length Data  

Data with varying size per element (face vertices, edge faces):

```
Data Buffer:   [face0_verts][face1_verts][face2_verts]...
Offset Buffer: [0][face0_end][face1_end][face2_end][total_end]
Access: face[i] = data[offset[i] : offset[i+1]]
```

### Attribute Storage

All attributes follow glTF 2.0 conventions:

- **Standard Attributes**: POSITION, NORMAL, TANGENT, TEXCOORD_0, COLOR_0, etc.
- **Custom Attributes**: Must use `_` prefix (e.g., `_WEIGHT`, `_CUSTOM_DATA`)
- **Buffer Views**: Each attribute stored in separate buffer view with proper typing

## Material Handling Strategy

EXT_bmesh_encoding resolves the tension between glTF's primitive-per-material model and BMesh's per-face materials through a dual representation approach:

### Export Strategy (BMesh → glTF)

**Primitive Optimization + Extension Preservation:**

```javascript
// 1. Group faces by material for optimal glTF primitives
function exportBmeshToGltf(bmesh) {
  const materialGroups = new Map();
  
  // Group faces by material
  for (const face of bmesh.faces) {
    const materialId = face.materialIndex;
    if (!materialGroups.has(materialId)) {
      materialGroups.set(materialId, []);
    }
    materialGroups.get(materialId).push(face);
  }
  
  // Create one glTF primitive per material for performance
  const primitives = [];
  for (const [materialId, faces] of materialGroups) {
    const triangles = triangulateFaces(faces);
    primitives.push({
      material: materialId,
      indices: createIndexBuffer(triangles),
      attributes: createAttributeBuffers(triangles),
      extensions: {
        EXT_bmesh_encoding: createBmeshExtension(faces) // Subset for this material
      }
    });
  }
  
  // Store complete per-face material mapping in extension
  const allFaceMaterials = bmesh.faces.map(face => face.materialIndex);
  
  return {
    primitives: primitives,
    // Complete BMesh extension data includes original per-face materials
    completeBmeshExtension: {
      // ... other BMesh data
      faces: {
        materials: createBufferView(allFaceMaterials), // Preserves original assignment
        // ... other face data
      }
    }
  };
}
```

### Import Strategy (glTF → BMesh)

**Extension Data as Authoritative Source:**

```javascript
// Reconstruct BMesh using extension data, not primitive materials
function importGltfToBmesh(gltfData) {
  const bmesh = {
    vertices: new Map(),
    edges: new Map(),
    loops: new Map(), 
    faces: new Map(),
  };
  
  const ext = gltfData.extensions.EXT_bmesh_encoding;
  
  // Reconstruct faces with original per-face materials
  const faceMaterials = readBufferView(buffers, bufferViews, ext.faces.materials);
  
  for (let i = 0; i < ext.faces.count; i++) {
    const face = {
      id: i,
      vertices: getFaceVertices(i, ext.faces),
      materialIndex: faceMaterials[i], // Use extension data, not primitive material
      // ... other face data
    };
    bmesh.faces.set(i, face);
  }
  
  return bmesh;
}
```

### Implementation Guidelines

**For Exporters:**
- **Performance First**: Group faces by material into separate glTF primitives
- **Preserve Fidelity**: Store original per-face material indices in extension data
- **Handle Mixed Materials**: Split multi-material BMesh objects into multiple primitives
- **Maintain Mapping**: Keep clear mapping between extension face indices and primitive faces

**For Importers:**
- **Extension Authority**: Use extension face materials as the authoritative source
- **Ignore Primitive Materials**: Primitive materials are optimization artifacts
- **Graceful Fallback**: When extension unavailable, infer materials from primitive assignment
- **Validate Consistency**: Check that extension data matches primitive grouping when possible

**For Viewers:**
- **Standard Rendering**: Use glTF primitives for efficient rendering (one draw call per material)
- **BMesh Operations**: Use extension data for topology operations requiring per-face materials
- **Hybrid Approach**: Combine both representations based on use case requirements

This approach ensures both **rendering performance** (optimized primitives) and **data fidelity** (complete BMesh reconstruction) without forcing a choice between them.

## Oriented 2-Manifold Validation

EXT_bmesh_encoding supports EXT_mesh_manifold compatibility through BMesh topology:

- **Halfedge Information**: Loop radial navigation provides halfedge structure
- **Manifold Detection**: Edge manifold flags indicate 2-manifold compliance  
- **Topology Validation**: Complete BMesh structure enables manifold verification
- **Graceful Handling**: Unknown manifold status (255) allows safe processing

## Implementation Notes

### Performance Considerations

- **Buffer Alignment**: Ensure proper 4-byte alignment for all buffer data
- **Memory Layout**: Optimize buffer view organization for sequential access
- **Compression**: Consider buffer compression for large datasets

### Compatibility  

- **glTF 2.0 Core**: Files work in any glTF 2.0 viewer via standard triangle mesh
- **Extension Support**: Enhanced features available when EXT_bmesh_encoding supported
- **Attribute Naming**: Strict adherence to glTF 2.0 attribute naming conventions
- **Buffer Management**: Standard glTF buffer view and accessor patterns throughout
