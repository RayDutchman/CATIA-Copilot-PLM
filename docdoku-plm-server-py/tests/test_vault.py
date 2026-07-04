import pytest
from pathlib import Path
from app.services.vault import (
    part_nativecad_path, part_geometry_path, part_attached_path
)

def test_nativecad_path_structure():
    """nativecad 路径规则：vault/{ws}/parts/{num}/{ver}/{iter}/nativecad/{filename}"""
    p = part_nativecad_path("WS1", "PART-001", "A", 1, "model.stp")
    assert str(p).endswith("WS1/parts/PART-001/A/1/nativecad/model.stp")

def test_geometry_path_structure():
    """geometry 路径规则：vault/{ws}/parts/{num}/{ver}/{iter}/geometry/{quality}.glb"""
    p = part_geometry_path("WS1", "PART-001", "A", 1, "LOW")
    assert str(p).endswith("WS1/parts/PART-001/A/1/geometry/LOW.glb")

def test_attached_path_structure():
    """attached 路径规则：vault/{ws}/parts/{num}/{ver}/{iter}/attachedfiles/{filename}"""
    p = part_attached_path("WS1", "PART-001", "A", 1, "drawing.pdf")
    assert str(p).endswith("WS1/parts/PART-001/A/1/attachedfiles/drawing.pdf")
