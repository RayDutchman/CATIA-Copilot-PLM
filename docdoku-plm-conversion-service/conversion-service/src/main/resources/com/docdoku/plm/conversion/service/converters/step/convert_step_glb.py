#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP to GLB converter using OpenCASCADE (via cadquery-ocp).

Usage:
    python3 convert_step_glb.py -i input.stp -o output.glb [--deflection 0.05] [--angular 0.3]

Arguments:
    -i / --inputFile        Path to input STEP file
    -o / --outputFile       Path to output GLB file
    --deflection            Relative chord deflection for triangulation (default: 0.05)
                            Smaller = more triangles = better quality
    --angular               Angular deflection in radians (default: 0.3 ~ 17 deg)
    -l / --freeCadLibPath   Ignored (kept for backward compatibility with Java caller)
"""

import sys
import os
import argparse
import struct

import numpy as np
import pygltflib

from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.XCAFDoc import (
    XCAFDoc_DocumentTool,
    XCAFDoc_ShapeTool,
    XCAFDoc_ColorType,
)
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFApp import XCAFApp_Application
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence
from OCP.Quantity import Quantity_Color
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopoDS import TopoDS_Face
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Convert STEP to GLB")
    parser.add_argument("-i", "--inputFile",      required=True)
    parser.add_argument("-o", "--outputFile",     required=True)
    parser.add_argument("-l", "--freeCadLibPath", default="",
                        help="Ignored (kept for Java caller compatibility)")
    parser.add_argument("--deflection", type=float, default=0.05,
                        help="Relative chord deflection (default 0.05 = 5%%)")
    parser.add_argument("--angular",    type=float, default=0.3,
                        help="Angular deflection in radians (default 0.3)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Shape downcast helper
# ---------------------------------------------------------------------------

def to_face(shape):
    """Downcast TopoDS_Shape to TopoDS_Face."""
    f = TopoDS_Face()
    f.TShape(shape.TShape())
    f.Location(shape.Location())
    f.Orientation(shape.Orientation())
    return f


# ---------------------------------------------------------------------------
# Read STEP with XDE (color-aware)
# ---------------------------------------------------------------------------

def read_step(filepath):
    """
    Read a STEP file and return (doc, shape_tool, color_tool, free_labels).
    doc MUST be kept alive by the caller for as long as shape_tool/labels are used —
    GC'ing doc will invalidate all TDF_Label handles.
    Colors are read via XDE CAF framework (works headless, OCC App layer).
    """
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    app.NewDocument(TCollection_ExtendedString("XmlOcaf"), doc)

    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    status = reader.ReadFile(filepath)
    if status.value != 1:  # IFSelect_RetDone = 1
        raise RuntimeError("STEP read failed, status=%s" % status)
    reader.Transfer(doc)

    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    labels = TDF_LabelSequence()
    st.GetFreeShapes(labels)

    return doc, st, ct, labels  # doc must be kept alive by caller!


# ---------------------------------------------------------------------------
# Get color for a shape (solid-level, then generic)
# ---------------------------------------------------------------------------

DEFAULT_COLOR = (0.8, 0.8, 0.8)  # light grey fallback

def get_shape_color(ct, shape):
    """
    Try to read surface color, then generic color.
    Returns (R, G, B) in [0, 1], or None if no color found.
    Gracefully handles null shapes (returns None).
    """
    try:
        if shape.IsNull():
            return None
        col = Quantity_Color()
        if ct.GetColor(shape, XCAFDoc_ColorType.XCAFDoc_ColorSurf, col):
            return (col.Red(), col.Green(), col.Blue())
        if ct.GetColor(shape, XCAFDoc_ColorType.XCAFDoc_ColorGen, col):
            return (col.Red(), col.Green(), col.Blue())
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Triangulate a shape and extract vertex/index data
# ---------------------------------------------------------------------------

def triangulate_shape(shape, deflection, angular):
    """
    Triangulate a TopoDS_Shape and return (vertices_np, indices_np).
    vertices_np: float32 array, shape (N, 3)
    indices_np:  uint32 array, shape (M, 3)
    """
    mesh = BRepMesh_IncrementalMesh(shape, deflection, True, angular)
    mesh.Perform()

    all_verts = []
    all_idx   = []
    v_offset  = 0

    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = to_face(exp.Current())
        loc  = face.Location()
        poly = BRep_Tool.Triangulation_s(face, loc)
        if poly is not None:
            # Apply location transform to vertices
            trsf = loc.IsIdentity()
            for j in range(1, poly.NbNodes() + 1):
                node = poly.Node(j)
                if not trsf:
                    node = node.Transformed(loc)
                all_verts.extend([float(node.X()),
                                   float(node.Y()),
                                   float(node.Z())])
            for j in range(1, poly.NbTriangles() + 1):
                n1, n2, n3 = poly.Triangle(j).Get()
                all_idx.extend([n1 - 1 + v_offset,
                                 n2 - 1 + v_offset,
                                 n3 - 1 + v_offset])
            v_offset += poly.NbNodes()
        exp.Next()

    if not all_verts:
        return None, None

    return (np.array(all_verts, dtype=np.float32).reshape(-1, 3),
            np.array(all_idx,   dtype=np.uint32).reshape(-1, 3))


# ---------------------------------------------------------------------------
# Collect (shape, color) pairs from XDE label tree
# ---------------------------------------------------------------------------

def collect_solid_colors(st, ct, labels):
    """
    Walk the free-shape labels, expanding assemblies recursively.
    Returns list of (shape, (R, G, B)).
    """
    result = []

    def visit(label, parent_color=None):
        shape = XCAFDoc_ShapeTool.GetShape_s(label)
        # shape can be null for reference labels — skip color query in that case
        color = (get_shape_color(ct, shape) if not shape.IsNull() else None) or parent_color

        # If this label is a component (reference), resolve its referred shape
        referred_labels = TDF_LabelSequence()
        if st.GetComponents_s(label, referred_labels, False):
            # Assembly: recurse into components
            for i in range(1, referred_labels.Size() + 1):
                visit(referred_labels.Value(i), color)
        else:
            # Leaf shape
            if not shape.IsNull():
                result.append((shape, color or DEFAULT_COLOR))

    for i in range(1, labels.Size() + 1):
        visit(labels.Value(i))

    # Fallback: if no leaves found, use the top-level shapes directly
    if not result:
        for i in range(1, labels.Size() + 1):
            label = labels.Value(i)
            shape = XCAFDoc_ShapeTool.GetShape_s(label)
            if shape.IsNull():
                continue
            color = get_shape_color(ct, shape) or DEFAULT_COLOR
            result.append((shape, color))

    return result


# ---------------------------------------------------------------------------
# Build GLB from list of (shape, color)
# ---------------------------------------------------------------------------

def build_glb(solid_colors, deflection, angular):
    """
    Triangulate each solid, assign its color as a separate material,
    and combine into one GLB scene.
    """
    meshes_primitives = []
    materials         = []
    accessors         = []
    buffer_views      = []
    byte_data         = bytearray()

    mat_index_map = {}  # (R,G,B) rounded -> material index

    def get_or_create_material(color):
        key = (round(color[0], 4), round(color[1], 4), round(color[2], 4))
        if key in mat_index_map:
            return mat_index_map[key]
        idx = len(materials)
        materials.append(pygltflib.Material(
            pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                baseColorFactor=[key[0], key[1], key[2], 1.0],
                metallicFactor=0.05,
                roughnessFactor=0.7,
            ),
            doubleSided=True,
        ))
        mat_index_map[key] = idx
        return idx

    node_indices = []

    for shape_idx, (shape, color) in enumerate(solid_colors):
        verts, idxs = triangulate_shape(shape, deflection, angular)
        if verts is None or len(verts) == 0:
            continue

        mat_idx = get_or_create_material(color)

        verts_b = verts.tobytes()
        idxs_b  = idxs.flatten().tobytes()

        # Buffer views
        bv_pos = pygltflib.BufferView(
            buffer=0,
            byteOffset=len(byte_data),
            byteLength=len(verts_b),
            target=pygltflib.ARRAY_BUFFER,
        )
        byte_data.extend(verts_b)

        bv_idx = pygltflib.BufferView(
            buffer=0,
            byteOffset=len(byte_data),
            byteLength=len(idxs_b),
            target=pygltflib.ELEMENT_ARRAY_BUFFER,
        )
        byte_data.extend(idxs_b)

        bv_pos_i = len(buffer_views)
        buffer_views.append(bv_pos)
        bv_idx_i = len(buffer_views)
        buffer_views.append(bv_idx)

        # Accessors
        acc_pos = pygltflib.Accessor(
            bufferView=bv_pos_i,
            componentType=pygltflib.FLOAT,
            count=len(verts),
            type=pygltflib.VEC3,
            max=verts.max(axis=0).tolist(),
            min=verts.min(axis=0).tolist(),
        )
        acc_idx = pygltflib.Accessor(
            bufferView=bv_idx_i,
            componentType=pygltflib.UNSIGNED_INT,
            count=idxs.size,
            type=pygltflib.SCALAR,
        )
        acc_pos_i = len(accessors)
        accessors.append(acc_pos)
        acc_idx_i = len(accessors)
        accessors.append(acc_idx)

        prim = pygltflib.Primitive(
            attributes=pygltflib.Attributes(POSITION=acc_pos_i),
            indices=acc_idx_i,
            material=mat_idx,
            mode=4,  # TRIANGLES
        )
        mesh_i = len(meshes_primitives)
        meshes_primitives.append([prim])
        node_indices.append(pygltflib.Node(mesh=mesh_i))

    if not node_indices:
        return None

    gltf = pygltflib.GLTF2(
        asset=pygltflib.Asset(version="2.0", generator="docdoku-plm-conversion-service"),
        scene=0,
        scenes=[pygltflib.Scene(nodes=list(range(len(node_indices))))],
        nodes=node_indices,
        meshes=[pygltflib.Mesh(primitives=prims) for prims in meshes_primitives],
        materials=materials,
        accessors=accessors,
        bufferViews=buffer_views,
        buffers=[pygltflib.Buffer(byteLength=len(byte_data))],
    )
    gltf.set_binary_blob(bytes(byte_data))
    return gltf


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    input_file  = args.inputFile
    output_file = args.outputFile
    deflection  = args.deflection
    angular     = args.angular

    if not input_file or not output_file:
        sys.exit("Error: -i and -o are required")

    if not os.path.exists(input_file):
        sys.exit("Error: input file not found: %s" % input_file)

    # Read STEP — doc must be kept alive until build_glb completes
    doc, st, ct, labels = read_step(input_file)

    # Collect solid/color pairs
    solid_colors = collect_solid_colors(st, ct, labels)

    # Build GLB
    gltf = build_glb(solid_colors, deflection, angular)
    if gltf is None:
        sys.exit("Error: no geometry generated from %s" % input_file)

    gltf.save_binary(output_file)
    size_kb = os.path.getsize(output_file) / 1024
    print("Converted %s -> %s (%.1f KB, %d solid(s))" % (
        os.path.basename(input_file),
        os.path.basename(output_file),
        size_kb,
        len(solid_colors)
    ))


if __name__ == "__main__":
    main()
