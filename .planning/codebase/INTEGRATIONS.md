# Novel Master - External Integrations

## 番茄小说 (Fanqie Novel)

**Platform**: https://fanqienovel.com

### Integration Type
Web browser automation via Playwright. The publish module (`fanqie_publish.py`) does not use a formal HTTP API. Instead, it:
1. Launches a Chromium browser with stored authentication cookies
2. Navigates to the author console (`fanqienovel.com/main/writer/`)
3. Performs chapter uploads via browser page interactions and JavaScript `fetch` calls executed in the page context

### Authentication
- **Method**: Playwright browser context storage state
- **Storage**: JSON file containing browser cookies and localStorage
- **Paths**:
  - Global: `~/.novel-master/fanqie-auth-state.json`
  - Per-project: `<project>/state/fanqie-auth-state.json`
- **Login flow**: Interactive — user completes login in a headed browser window; script polls every 2 seconds for up to 180 seconds to detect success

### API Endpoints (called via page-executed fetch)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/author/homepage/book_list/v0/` | GET | List author's books |
| `/api/author/book/create/v0/` | POST | Create new book |
| `/api/author/article/new_article/` | POST | Save chapter to draft |
| `/api/author/article/cover_article/` | POST | Update existing draft |

### Book Publishing Flow

1. **Create book** → Returns `book_id`, stored in `state/fanqie-publish-state.json`
2. **Upload chapter** → Browser form at `fanqienovel.com/main/writer/{book_id}/publish/`
   - Fills chapter number (left input)
   - Fills chapter title (input placeholder "标题")
   - Fills content via ProseMirror editor (`document.querySelector('.ProseMirror')`)
   - Clicks "存草稿" (Save Draft) button
3. **Track state** → `state/fanqie-publish-state.json` records uploaded chapters

### Genre/Category Mapping

```
男频: 玄幻(1), 奇幻(2), 武侠(3), 仙侠(4), 都市(5), 历史(7),
      军事(8), 游戏(9), 竞技(10), 科幻(11), 灵异(12), 二次元(13), 末世(21)
女频: 古代言情(14), 现代言情(15), 幻想言情(16), 青春校园(19), 悬疑推理(20)
```

### Rate Limits
- **Daily upload limit**: 50,000 characters per upload session

### External Resources Referenced

| Resource | Purpose |
|----------|---------|
| `https://fanqienovel.com/main/writer/` | Author console entry point |
| `https://fanqienovel.com/main/writer/{book_id}/publish/` | Chapter submission page |
| 番茄作家后台 | Manual publishing review workflow (outside CLI scope) |

---

## Internal Integrations

### Corpus Analysis (Local)

The corpus module (`search_corpus.py`) reads from local files:
- `corpus/articles/*.md` — Raw articles
- `corpus/analysis/excerpts.csv` — Structured excerpts with tags and types
- `corpus/analysis/article_profiles.csv` — Article metadata
- `corpus/analysis/stats.json` — Aggregated statistics

### State Synchronization

| Component | Data Flow |
|-----------|-----------|
| `quality_gate.py` → `state.json` | Updates `completed_chapters`, `current_chapter`, `latest_events` |
| `story_graph.py post-write` → `timeline.md` | Appends chapter events |
| `story_graph.py post-write` → `event_matrix.json` | Logs chapter event type |
| `story_graph.py post-write` → `story_graph.json` | Attribute tracking with chapter timestamps |
| `init_project.py` → All project files | Generates complete project scaffold |

### Knowledge Graph (In-Memory JSON)

Nodes and edges are managed via `story_graph.py`:
- **Node types**: character, location, faction, item, event, foreshadowing, world_rule, power_system
- **Edge types**: ally, enemy, mentor, subordinate, emotional, belongs_to, located_at, triggers, foreshadows, possesses, related_to

---

## Third-Party Skill Integrations (Documented in Code)

The codebase references external open-source skills in comments:

| Referenced Project | Purpose |
|-------------------|---------|
| `leenbj/novel-creator-skill` | 7-category AI-flavour detection patterns |
| `op7418/Humanizer-zh` | 24 humanization patterns |
| `Tomsawyerhu/Chinese-WebNovel-Skill` | Anti-AI writing principles + corpus structure |

These are **not installed as dependencies** — patterns are embedded directly in `anti_ai_detector.py` and referenced in `search_corpus.py` docstrings.

---

## Auth & Security Notes

- Browser session files (`fanqie-auth-state.json`) contain sensitive cookies — they are gitignored
- No secret keys or tokens stored in codebase
- Fanqie auth state uses Playwright's native browser storage state format (not a custom token system)
