#!/usr/bin/env python3
"""T2: Static scan + runtime assert that no cv2.rectangle/putText/ImageDraw.Draw
reaches the render path (compositor.py, reframe.py).

These functions live ONLY in debug.py. If any render module imports them,
debug artifacts could bake into output frames — an instant pipeline failure.
"""
import ast
import os
import sys
import unittest

VERTICAL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Prohibited calls in the render path
PROHIBITED_ATTRS = {
    "rectangle", "putText", "circle", "arrowedLine", "polylines",
    "drawContours", "fillPoly", "line",
}
PROHIBITED_CLASSES = {"ImageDraw", "Draw"}
PROHIBITED_IMPORTS = {"ImageDraw"}


class ProhibitedCallVisitor(ast.NodeVisitor):
    """AST visitor that flags prohibited drawing calls."""

    def __init__(self):
        self.violations = []

    def visit_Attribute(self, node):
        if node.attr in PROHIBITED_ATTRS:
            self.violations.append(
                f"line {node.lineno}: prohibited call .{node.attr}()")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and "ImageDraw" in node.module:
            self.violations.append(
                f"line {node.lineno}: prohibited import from {node.module}")
        if node.names:
            for alias in node.names:
                if alias.name in PROHIBITED_IMPORTS:
                    self.violations.append(
                        f"line {node.lineno}: prohibited import {alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node):
        # Catch ImageDraw.Draw(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "Draw":
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "ImageDraw":
                        self.violations.append(
                            f"line {node.lineno}: prohibited ImageDraw.Draw()")
        self.generic_visit(node)


class TestRenderIsolation(unittest.TestCase):
    """T2: No debug drawing in render path modules."""

    def _check_file(self, filename):
        path = os.path.join(VERTICAL_DIR, filename)
        if not os.path.exists(path):
            self.skipTest(f"{filename} not yet created")
        with open(path) as f:
            source = f.read()
        tree = ast.parse(source, filename=filename)
        visitor = ProhibitedCallVisitor()
        visitor.visit(tree)
        if visitor.violations:
            msg = f"\n{filename} has prohibited drawing calls:\n"
            msg += "\n".join(f"  {v}" for v in visitor.violations)
            self.fail(msg)

    def test_compositor_no_debug_drawing(self):
        self._check_file("compositor.py")

    def test_reframe_no_debug_drawing(self):
        self._check_file("reframe.py")

    def test_shotmap_no_debug_drawing(self):
        """shotmap.py may use PIL for contact_sheet but NOT cv2 drawing on frames."""
        path = os.path.join(VERTICAL_DIR, "shotmap.py")
        if not os.path.exists(path):
            self.skipTest("shotmap.py not yet created")
        with open(path) as f:
            source = f.read()
        tree = ast.parse(source, filename="shotmap.py")
        visitor = ProhibitedCallVisitor()
        visitor.visit(tree)
        # Filter: allow drawing calls inside contact_sheet function only
        # (contact_sheet is a diagnostic output function, not part of the render path)
        contact_range = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "contact_sheet":
                contact_range = (node.lineno, node.end_lineno)
                break
        real_violations = []
        for v in visitor.violations:
            line_no = int(v.split("line ")[1].split(":")[0])
            if contact_range and contact_range[0] <= line_no <= contact_range[1]:
                continue  # allowed inside contact_sheet
            real_violations.append(v)
        if real_violations:
            self.fail(f"shotmap.py violations outside contact_sheet:\n" +
                      "\n".join(f"  {v}" for v in real_violations))


class TestLayoutConstancy(unittest.TestCase):
    """T3: Layout ID is constant within shotmap boundaries.
    This test validates that shot_map.json entries each have a single layout."""

    def test_shot_map_layout_constant(self):
        shot_map_path = os.path.join(VERTICAL_DIR, "work", "shot_map.json")
        if not os.path.exists(shot_map_path):
            self.skipTest("No shot_map.json yet (run shotmap first)")
        import json
        with open(shot_map_path) as f:
            data = json.load(f)
        for shot in data.get("shots", []):
            layout = shot.get("layout")
            self.assertIsNotNone(layout,
                                 f"Shot {shot.get('id')} has no layout")
            self.assertIn(layout,
                          ("single", "2up", "3up", "4up", "5up", "grid",
                           "screenshare", "unmeasured"),
                          f"Shot {shot.get('id')} has unknown layout: {layout}")


if __name__ == "__main__":
    unittest.main()
