#!/usr/bin/env python3
"""Phase 3: 对全部 GET 路由自动补尾斜杠双路由。"""
import re, sys
from pathlib import Path

ROUTERS = Path("/home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-server-py/app/routers")

files = sorted(ROUTERS.glob("*.py"))
total = 0

for f in files:
    lines = f.read_text().split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 匹配多种格式:
        # @router.get("/path")
        # @router.get(f"{PREFIX}/path")
        # @router.get("/path/{param}")
        # @router.get(f"{PREFIX}/path/{param}")
        
        m = re.match(r'^(\s*@router\.get\()"([^"]+)"\)\s*$', line)
        if not m:
            m = re.match(r'^(\s*@router\.get\()(\w+\s*\+\s*)"([^"]+)"\)\s*$', line)  # f"{PREFIX}" + "/path" pattern... too complex
        if not m:
            # try: @router.get(f"{PREFIX}/path"), capture prefix + path
            m = re.match(r'^(\s*@router\.get\()f"(\{[^}]+\})(/[^"]*)"\)\s*$', line)
            if m:
                indent = m.group(1)
                prefix = m.group(2)
                path = prefix + m.group(3)
            else:
                new_lines.append(line)
                i += 1
                continue
        else:
            indent = m.group(1)
            path = m.group(2)
        
        if path.endswith("/"):
            new_lines.append(line)
            i += 1
            continue
        
        # Check if next line is already the hidden variant
        next_hidden = (i + 1 < len(lines) and
                      'include_in_schema=False' in lines[i + 1] and
                      'router.get' in lines[i + 1])
        if next_hidden:
            new_lines.append(line)
            i += 1
            continue
        
        # Build trailing slash line
        # Reconstruct from original line
        orig = lines[i].rstrip()
        # Replace last ")" with /) and add include_in_schema
        if 'f"' in orig:
            # f-string pattern: @router.get(f"{PREFIX}/path")
            slash_line = orig.replace('")', '/", include_in_schema=False)')
        else:
            # plain string: @router.get("/path")
            slash_line = orig.replace('")', '/", include_in_schema=False)')
        
        new_lines.append(line)
        new_lines.append(slash_line)
        total += 1
        i += 1
    
    f.write_text("\n".join(new_lines) + "\n")

print(f"Added {total} trailing-slash GET routes across {len(files)} router files")
