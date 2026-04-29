# Coding Conventions — Novel Master

## Overview

This codebase is a Python-based CLI toolkit for novel writing and publishing. All scripts follow consistent conventions documented here.

---

## 1. Script Structure

### Header Template

```python
#!/usr/bin/env python3
"""Novel Master: [Brief one-line description]"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
```

### Imports

- Standard library first, then third-party
- Local imports from `utils.py` use `from utils import ...`
- Type imports grouped: `from typing import Dict, List, Optional, Tuple`

---

## 2. Type Annotations

All functions use type hints.

```python
def check_word_count(text: str, chapter_num: int = 0, writing_type: str = "medium") -> Dict:
def add_node(project_root: Path, node_id: str, node_type: str, name: str,
             properties: Optional[Dict] = None, chapter_intro: Optional[int] = None):
def detect_chapter(text: str) -> Dict:
```

---

## 3. Constants

Module-level constants use `UPPER_SNAKE_CASE` and are defined before functions.

```python
WRITING_TYPES = {
    "short": {"label": "短篇", "default_chapters": 8, ...},
    "medium": {...},
}

EVENT_TYPES = {
    "conflict_thrill": "冲突高潮",
    "bond_deepening": "情感升温",
}

AI_PATTERNS = {
    "高频AI词汇": {"weight": 2, "words": [...]},
}
```

---

## 4. CLI Design — argparse Subcommands

Complex CLIs use `add_subparsers` with a `command` dest.

```python
def main():
    parser = argparse.ArgumentParser(description="Novel Master: ...")
    sub = parser.add_subparsers(dest="action", required=True)

    # Each subcommand
    p_node = sub.add_parser("add-node", help="...")
    p_node.add_argument("--id", required=True)
    p_node.add_argument("--type", required=True, choices=list(NODE_TYPES.keys()))

    args = parser.parse_args()

    if args.action == "add-node":
        add_node(proj, args.id, ...)
    elif args.action == "check":
        ...
```

### Standard Argument Patterns

| Argument | Flag | Purpose |
|----------|------|---------|
| project root | `-p`, `--project` | Target project directory |
| chapter | `-c`, `--chapter` | Chapter number |
| force | `--force` | Skip safety checks |

### Exit Codes

- `0` — success
- `1` — failure
- Use `sys.exit(1)` or `return 1` from `main()`

---

## 5. JSON State Files

### Read/Write Pattern

```python
def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

### State File Structure

State files track timestamps and versions:

```python
{
    "version": 1,
    "last_updated": "2026-04-28T19:06:00.000000",
    ...
}
```

---

## 6. File Paths

Use `pathlib.Path` exclusively.

```python
from pathlib import Path

project_root = Path(args.project)
state_file = project_root / "state" / "current" / "state.json"
gate_file = project_root / "gates" / f"第{chapter_num:03d}章-gate.json"
```

### Directory Creation

```python
def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
```

---

## 7. Return Value Patterns

### Check Functions

Return a `Dict` with a `status` field:

```python
result = {
    "status": "pass",      # or "warn", "fail"
    "count": 3200,
    "min": 3000,
    "max": 3500,
    "issues": [],
    "iron_rule": False,
}
```

### Command Results

Return `Dict` for structured data or `None` for void commands.

---

## 8. Error Handling

```python
try:
    state = read_json(state_file)
except Exception:
    chapter = 1

# Graceful degradation
if state_file.exists():
    state = read_json(state_file)
else:
    state = {}
```

---

## 9. Graph/Node Data Structure

Knowledge graph stored as:

```python
{
    "nodes": [
        {
            "id": "character_01",
            "type": "character",
            "name": "李四",
            "properties": {},
            "attributes": [{"key": "身份", "value": "大理寺捕快", "chapter": 5}],
            "chapter_intro": 1,
            "created_at": "2026-04-28T..."
        }
    ],
    "edges": [
        {
            "source": "character_01",
            "target": "location_01",
            "type": "located_at",
            "properties": {},
            "created_at": "..."
        }
    ],
    "version": 1,
    "last_updated": "..."
}
```

---

## 10. Markdown Generation

Utility for writing markdown:

```python
def write_md(path: Path, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
```

---

## 11. Naming

| Kind | Convention | Example |
|------|------------|---------|
| Functions | `snake_case` | `check_word_count` |
| Constants | `UPPER_SNAKE_CASE` | `EVENT_TYPES` |
| Types | PascalCase | `Dict`, `List` |
| CLI args | `snake_case` | `--chapter_num` |
| JSON keys | `snake_case` | `chapter_intro` |

---

## 12. Module Organization

```
scripts/
├── utils.py              # Shared utilities (file I/O, constants, helpers)
├── story_graph.py        # Knowledge graph management
├── quality_gate.py       # Chapter quality checks
├── anti_ai_detector.py   # AI-flavor detection
├── event_matrix.py       # Event tracking and rhythm
├── init_project.py       # Project scaffolding
├── fanqie_publish.py     # Platform publishing (async/Playwright)
└── search_corpus.py      # Corpus search
```

### Dependencies

- `utils.py` has no dependencies on other scripts
- All other scripts import from `utils.py`
- `fanqie_publish.py` has try/except fallback for its own import

---

## 13. Async Pattern

Used only in `fanqie_publish.py` for Playwright:

```python
async def cmd_upload(args):
    ...
    pw, browser, context, page = await _launch_browser(auth_path)
    try:
        ...
    finally:
        await browser.close()
        await pw.stop()
```

---

## 14. Shebang and Encoding

All scripts begin with:

```python
#!/usr/bin/env python3
```

Python 3 defaults to UTF-8; no explicit encoding declaration needed.
