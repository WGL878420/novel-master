# Architecture

**Analysis Date:** 2026-04-29

## Pattern Overview

**Overall:** CLI-based workflow orchestration with state management

**Key Characteristics:**
- Pure Python CLI scripts (no web framework) - runs via `python3 scripts/<script>.py`
- Stateful project-based organization with JSON state files
- Markdown-first content storage (chapters, bible, knowledge)
- Modular single-responsibility scripts communicating via files
- Async/await for I/O-bound operations (Playwright browser automation)

## Layers

**CLI Scripts Layer:**
- Purpose: User-facing commands for all novel writing operations
- Location: `scripts/`
- Contains: Entry point scripts (story_graph.py, quality_gate.py, init_project.py, fanqie_publish.py, anti_ai_detector.py, event_matrix.py)
- Depends on: utils.py (shared utilities)
- Used by: User via command line

**Shared Utilities Layer:**
- Purpose: Common functions used across all scripts
- Location: `scripts/utils.py`
- Contains: File I/O, chapter parsing, Chinese character counting, writing type configuration
- Depends on: None (stdlib only)
- Used by: All CLI scripts

**State Management Layer:**
- Purpose: Persistent project state via JSON files
- Location: `<project>/state/current/state.json`, `<project>/state/template/state.json`
- Contains: Project metadata, progress tracking, sync status, fanqie config
- Depends on: CLI scripts (write), User (read via scripts)
- Format: JSON with nested structure for project, progress, summary, config, fanqie

**Knowledge Graph Layer:**
- Purpose: Track characters, locations, events, foreshadowing as nodes and edges
- Location: `<project>/knowledge/story_graph.json`, `<project>/knowledge/event_matrix.json`, `<project>/knowledge/timeline.md`
- Contains: Nodes (entities), Edges (relationships), Event records, Timeline entries
- Depends on: CLI scripts for mutations
- Format: JSON graph structure + Markdown timeline

**Content Layer:**
- Purpose: The actual novel content
- Location: `<project>/bible/` (planning), `<project>/manuscript/` (written chapters)
- Contains: World-building, character profiles, outline, style guide, research, chapter files
- Depends on: CLI scripts for generation and validation
- Format: Markdown files

**Validation/Gate Layer:**
- Purpose: Quality enforcement before content acceptance
- Location: `<project>/gates/` (pass/fail records)
- Contains: Gate check results per chapter
- Depends on: quality_gate.py
- Format: JSON per chapter

## Data Flow

**Project Initialization:**
1. User runs `python3 scripts/init_project.py "书名" --genre 题材`
2. init_project.py generates bible content based on genre keywords
3. Creates directory structure: bible/, manuscript/, knowledge/, state/, gates/
4. Initializes state.json, story_graph.json, event_matrix.json, timeline.md

**Writing Flow:**
1. User writes chapter manually (no script generates prose)
2. Runs `python3 scripts/quality_gate.py check -p <project>` - five-step validation
3. If word count fails iron rule: chapter must be rewritten (no gate record saved)
4. If pass: gate record saved, state.json updated with progress
5. Runs `python3 scripts/story_graph.py -p <project> post-write --chapter N` automatically
6. post-write updates timeline, event_matrix, synced_up_to_chapter marker

**Knowledge Graph Flow:**
1. `story_graph.py brief` generates writing brief from current state
2. `story_graph.py add-node/add-edge/add-attr` modifies knowledge graph
3. `story_graph.py check-continuity` validates graph consistency
4. Graph used by brief for context, not directly by other scripts

**Publishing Flow (Optional):**
1. `fanqie_publish.py setup` - install Playwright + login
2. `fanqie_publish.py create-book` - creates book via API, saves book_id
3. `fanqie_publish.py upload` - uploads chapters via browser automation
4. State saved to `<project>/state/fanqie-publish-state.json`
5. Auth state persisted to `~/.novel-master/fanqie-auth-state.json`

## Key Abstractions

**Writing Type Configuration:**
- Purpose: Defines word count rules per chapter based on project type
- Examples: `scripts/utils.py` WRITING_TYPES constant
- Pattern: Dictionary mapping type keys (short/medium/long/tomato) to config with word_limits or phased rules

**Chapter File Naming:**
- Purpose: Standardized chapter file identification
- Examples: `manuscript/第001章-相机.md`, `manuscript/第002章-灵照相.md`
- Pattern: `第{XXX}章-{title}.md` where XXX is zero-padded 3-digit number

**Bible Structure:**
- Purpose: Project planning and reference documents
- Examples: `bible/00-world-building.md`, `bible/01-character-profiles.md`, `bible/02-style-guide.md`, `bible/03-outline.md`, `bible/04-research.md`
- Pattern: Numbered prefix for order, semantic naming

**Gate Check Results:**
- Purpose: Quality validation records
- Examples: `gates/第001章-gate.json`
- Pattern: JSON with chapter number, timestamp, overall status, individual check results

**Story Graph (Knowledge Graph):**
- Purpose: Track entities and relationships as a graph
- Examples: `knowledge/story_graph.json`
- Pattern: Nodes array + Edges array, nodes have type (character/location/faction/etc), edges have source/target/type

## Entry Points

**init_project.py:**
- Location: `scripts/init_project.py`
- Triggers: `python3 scripts/init_project.py <name> [options]`
- Responsibilities: Create new project directory structure with genre-aware bible content

**story_graph.py:**
- Location: `scripts/story_graph.py`
- Triggers: Multiple subcommands via argparse subparsers
- Responsibilities: Knowledge graph CRUD, brief generation, post-write sync, outline extension
- Subcommands: add-node, add-edge, add-attr, related, check, check-continuity, brief, extend-outline, post-write, check-bible, sync-status, resolve-fs

**quality_gate.py:**
- Location: `scripts/quality_gate.py`
- Triggers: `python3 scripts/quality_gate.py check -p <project> [--chapter N]`
- Responsibilities: Five-step validation (word count, opening grab, hook, AI indicators, conflict)

**fanqie_publish.py:**
- Location: `scripts/fanqie_publish.py`
- Triggers: Multiple subcommands
- Responsibilities: Browser-based authentication, book creation, chapter upload via Playwright
- Subcommands: setup, login, list-books, create-book, upload, status

**anti_ai_detector.py:**
- Location: `scripts/anti_ai_detector.py`
- Triggers: `python3 scripts/anti_ai_detector.py [detect|report|polish] <file>`
- Responsibilities: AI flavor detection, quality assessment, polish prompts

**event_matrix.py:**
- Location: `scripts/event_matrix.py`
- Triggers: `python3 scripts/event_matrix.py [add|check|rhythm|suggest] -p <project>`
- Responsibilities: Event type tracking, cooldown management, rhythm health checks

## Error Handling

**Strategy:** Fail fast with clear messages, distinguish iron rules from warnings

**Patterns:**
- Iron rule violations (word count too low): Exit with non-zero code, do not save gate record, require rewrite
- Soft failures (warnings): Save gate record with conditional_pass status, continue workflow
- Missing files: Graceful handling with clear error messages suggesting fixes
- Import errors: Fallback sys.path manipulation in fanqie_publish.py

## Cross-Cutting Concerns

**Logging:** Print-based output with emoji indicators (✅ ❌ ⚠️), no structured logging library

**Validation:** Centralized in quality_gate.py - five mandatory checks per chapter

**Authentication:** Browser session persistence via Playwright storage_state, saved to ~/.novel-master/

**State Consistency:** Sync markers (synced_up_to_chapter) prevent drift between manuscript and knowledge graph

---

*Architecture analysis: 2026-04-29*
