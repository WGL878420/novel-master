# Codebase Concerns

**Analysis Date:** 2026-04-29

## Tech Debt

**AI Pattern Detection Duplication:**
- Issue: `anti_ai_detector.py` and `quality_gate.py` both define AI味 detection patterns independently
- Files: `scripts/anti_ai_detector.py` (lines 21-135), `scripts/quality_gate.py` (lines 93-101)
- Impact: Maintenance burden - patterns must be updated in two places
- Fix approach: Extract shared patterns to `utils.py` as a shared constant

**Dual Chapter Parsing Logic:**
- Issue: `fanqie_publish.py` has two similar functions for parsing chapter files
- Files: `_parse_chapter_file` (lines 291-320), `_parse_chapter_browser` (lines 323-357)
- Impact: Code duplication, potential inconsistency between file parsing modes
- Fix approach: Consolidate into single `parse_chapter()` function with mode parameter

**Silent Empty Returns:**
- Issue: Several functions return empty collections on error without logging or raising
- Files:
  - `scripts/search_corpus.py:32` - returns `[]` when corpus not ready
  - `scripts/fanqie_publish.py:238` - returns `[]` on API failure
  - `scripts/story_graph.py:447` - returns `{}` silently
  - `scripts/utils.py:135` - returns `[]` for empty chapter files
- Impact: Errors mask themselves, making debugging difficult
- Fix approach: Add error logging or raise descriptive exceptions

**No Dependency Pinning:**
- Issue: No `requirements.txt` or `pyproject.toml` - dependencies installed ad-hoc
- Files: None (no lock file exists)
- Impact: Breaking changes from library updates can silently break functionality
- Fix approach: Create `requirements.txt` with version pins

## Known Bugs

**CJK Character Range May Miss Rare Characters:**
- Issue: `count_chinese_chars()` uses regex `[一-鿿]` which may not cover all Chinese characters
- File: `scripts/utils.py:128`
- Trigger: Very rare Chinese characters outside the range
- Workaround: Most common Chinese text is covered; rare edge cases unaffected for web novel writing

**Regex-Based Bible Field Detection Fragile:**
- Issue: `check_bible()` uses regex `^[-*]\s+\*{0,2}\S+\*{0,2}：` which could miss or mis-match fields
- File: `scripts/story_graph.py:475-478`
- Trigger: Non-standard formatting in bible files
- Workaround: Manual bible checking advised

**File Path Globbing in `update_project_state`:**
- Issue: Uses `glob()` which can match incorrectly if multiple chapter files exist
- File: `scripts/quality_gate.py:159-161`
- Trigger: Multiple files matching `第{chapter_num:03d}章-*.md` pattern
- Workaround: Ensure only one chapter file per number exists

## Security Considerations

**Browser Authentication State Stored on Disk:**
- Risk: `fanqie-auth-state.json` contains session cookies saved by Playwright
- Files: `scripts/fanqie_publish.py:82-90` (auth state path resolution)
- Current mitigation: Stored in `~/.novel-master/` or project `state/` directory, gitignored
- Recommendations: Document that these files should never be committed; add pre-commit hook to prevent accidental commit

**Browser Automation Detection Bypass:**
- Risk: `_launch_browser()` passes `--disable-blink-features=AutomationControlled` flag
- File: `scripts/fanqie_publish.py:116`
- Current mitigation: Used only for legitimate publisher automation
- Recommendations: This technique could be flagged by anti-bot systems;番茄 may change their detection

**No Input Validation on Project Paths:**
- Risk: User-provided paths not validated before file operations
- Files: Throughout - all `project_root` Path arguments
- Current mitigation: None
- Recommendations: Validate paths exist and are within expected directories

## Performance Bottlenecks

**Repeated File I/O in `generate_brief`:**
- Problem: Every `brief` call reads multiple JSON/MD files sequentially
- File: `scripts/story_graph.py:213-352`
- Cause: No caching; called frequently during writing workflow
- Improvement path: Add simple in-memory cache with TTL for project state

**Sorting Chapters Without Index:**
- Problem: `get_chapter_files()` does full glob + sort every call
- File: `scripts/utils.py:131-137`
- Cause: No indexing mechanism for chapter files
- Improvement path: Build chapter index once, update on changes

**Large Bible File Regex Scanning:**
- Problem: `check_bible()` scans entire bible files with regex on each call
- File: `scripts/story_graph.py:442-503`
- Cause: No incremental checking
- Improvement path: Cache bible file analysis results

## Fragile Areas

**Playwright Login Detection Heuristic:**
- Files: `scripts/fanqie_publish.py:144-165`, `scripts/fanqie_publish.py:168-175`
- Why fragile: Relies on string matching in page body text - any UI text change breaks it
- Safe modification: If modifying, test against actual 番茄 writer backend UI
- Test coverage: No automated tests for login detection

**Chapter Number Extraction from Filename:**
- Files: `scripts/utils.py:120-123`, `scripts/fanqie_publish.py:296-299, 329-330`
- Why fragile: Regex `(\d+)` extracts first number in filename - could be wrong if filename has multiple numbers
- Safe modification: Ensure only one numeric sequence in chapter filenames
- Test coverage: No automated tests

**Event Matrix Cooldown Logic:**
- File: `scripts/event_matrix.py:55-75`
- Why fragile: Assumes chapters are sequential and contiguous; gaps cause cooldown miscalculation
- Safe modification: Handle non-sequential chapters explicitly
- Test coverage: No automated tests

**Story Graph Attribute Conflict Detection:**
- File: `scripts/story_graph.py:105-107`
- Why fragile: Simple value equality check - doesn't understand semantic equivalence ("京城" vs "长安" might be same place)
- Safe modification: Document that location names must be consistent
- Test coverage: No automated tests

## Scaling Limits

**Single-User Architecture:**
- Current capacity: Designed for single writer per project
- Limit: No support for multiple concurrent writers or conflict resolution
- Scaling path: Not applicable - single-user tool

**Project State in Single JSON File:**
- Current capacity: `state.json` grows linearly with chapter count
- Limit: Very large novels (1000+ chapters) might hit file size/parsing performance issues
- Scaling path: Consider chapter-scoped state files for extremely long works

**In-Memory Graph for Large Knowledge Graphs:**
- Current capacity: Entire `story_graph.json` loaded into memory
- Limit: Projects with thousands of nodes/edges may hit memory limits
- Scaling path: Implement graph database or paginated loading for large projects

## Dependencies at Risk

**Playwright as Required Dependency for Publishing:**
- Risk: Heavy dependency (requires browser installation), may fail to install on some systems
- Impact: Fanqie publishing completely unavailable if Playwright fails
- Migration plan: Could fall back to HTTP API-based upload if番茄 provides one; current browser approach is intentional fallback

**No Test Framework:**
- Risk: No automated testing means regressions undetected
- Impact: Any refactoring or feature addition could break existing functionality
- Migration plan: Add `pytest` with basic smoke tests for core utilities

## Missing Critical Features

**No Automated Backup:**
- Problem: Project files (manuscript, bible, state) have no automatic backup mechanism
- Blocks: Risk of data loss on system failure
- Priority: High

**No Chapter Diff/Version History:**
- Problem: No way to see what changed between chapter versions
- Blocks: Cannot track writing evolution or easily revert bad edits
- Priority: Medium

**No Concurrent Safety:**
- Problem: No file locking - simultaneous writes from multiple processes could corrupt state
- Blocks: Cannot run multiple writing sessions or automated tools in parallel
- Priority: Medium

## Test Coverage Gaps

**Untested Core Utilities:**
- What's not tested: `count_chinese_chars`, `chapter_number`, `get_chapter_files`
- Files: `scripts/utils.py`
- Risk: Character counting or chapter parsing bugs would silently produce wrong results
- Priority: High

**Untested Quality Gate:**
- What's not tested: Gate check logic with real chapter text
- Files: `scripts/quality_gate.py`
- Risk: Quality gate might pass/fail incorrectly for borderline cases
- Priority: High

**Untested AI Detection:**
- What's not tested: Pattern matching and density calculation accuracy
- Files: `scripts/anti_ai_detector.py`
- Risk: AI味 reports could be inaccurate
- Priority: Medium

**No Integration Tests:**
- What's not tested: End-to-end workflow (write -> gate -> post-write -> publish)
- Files: N/A
- Risk: Commands may not compose correctly in real workflow
- Priority: High

---

*Concerns audit: 2026-04-29*
