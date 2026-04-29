# Novel Master - Technology Stack

## Languages & Runtime

- **Python 3** — Primary language for all CLI tools and scripts
- **Shell** — Bash/zsh for project initialization and CLI wrapper scripts

## Core Dependencies

All dependencies are pure Python standard library, except one optional package:

| Package | Purpose | Required |
|--------|---------|----------|
| `playwright` | Browser automation for 番茄小说 publishing | Optional |

### Standard Library Modules Used

- `argparse` — CLI argument parsing
- `json` — State and data serialization
- `re` — Text pattern matching (chapter parsing, Chinese char counting)
- `pathlib` — Cross-platform path manipulation
- `datetime` — Timestamp handling
- `csv` — Corpus analysis exports
- `asyncio` — Async browser control (Playwright)

## Scripts Architecture

```
scripts/
├── init_project.py          # Project scaffolding generator
├── quality_gate.py          # 5-step chapter quality enforcement
├── anti_ai_detector.py      # AI-flavour detection (7 categories, 24 patterns)
├── story_graph.py           # Knowledge graph & character tracking
├── event_matrix.py          # Event rhythm & cooldown tracking
├── search_corpus.py         # Local corpus search
├── fanqie_publish.py        # 番茄小说 web publishing (Playwright)
└── utils.py                 # Shared utilities (file I/O, chapter parsing, word counting)
```

## File Storage

- **State**: JSON files (`state.json`)
- **Knowledge Graph**: JSON (`story_graph.json`)
- **Event Matrix**: JSON (`event_matrix.json`)
- **Manuscript**: Markdown files (`第NNN章-*.md`)
- **Bible**: Markdown reference files (`bible/*.md`)
- **Gates**: JSON quality gate records (`gates/第NNN章-gate.json`)

## Writing Type Configurations

| Type | Label | Word Limits | Phased |
|------|-------|-------------|--------|
| `short` | 短篇 | 2000-4000 | No |
| `medium` | 中篇 | 3000-5000 | No |
| `long` | 长篇 | 3000-5000 | No |
| `tomato` | 番茄连载 | 3000-3500 | Yes (3 phases) |

## Project Structure

```
project/
├── bible/           # Writing reference (world-building, characters, outline, style)
├── state/           # Project state (current/template)
│   └── current/state.json
├── manuscript/      # Chapter markdown files
├── knowledge/       # Graph, matrix, timeline
│   ├── story_graph.json
│   ├── event_matrix.json
│   └── timeline.md
└── gates/          # Quality gate records
```

## Configuration Files

- `CLAUDE.md` — Project instructions (this file is the main specification)
- `.claude/scheduled_tasks.json` — Persistent cron jobs
- `~/.novel-master/fanqie-auth-state.json` — Browser session storage (global)
- Project-level `state/fanqie-auth-state.json` — Per-project browser session
- Project-level `state/fanqie-publish-state.json` — Publishing state & uploaded chapters

## Corpus

- `corpus/articles/` — Raw reference articles (Markdown)
- `corpus/analysis/excerpts.csv` — Tagged excerpts
- `corpus/analysis/article_profiles.csv` — Article metadata
- `corpus/analysis/stats.json` — Corpus statistics

## Templates

- `templates/state/template/state.json` — Project state template
- `templates/plan/writing-plan-template.json` — Writing plan template
