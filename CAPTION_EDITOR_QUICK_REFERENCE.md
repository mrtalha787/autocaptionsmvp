# Caption Editor - Quick Reference & FAQs

## Q: What's the simplest way to start?

**A:** Use the Hybrid approach:
1. Keep Streamlit as main app
2. Add "Edit Captions" button that opens a separate React page
3. Use FastAPI to bridge them
4. No need to rewrite Streamlit interface

**Estimated effort:** 7-10 days

---

## Q: Can I do this without React?

**A:** Technically yes, but:
- **Streamlit-only**: Rough, limited real-time performance, janky timeline
- **With React**: Smooth, professional, responsive

**Recommendation:** Invest in React for better UX

---

## Q: How do I handle large videos (>1GB)?

**A:** Use HLS streaming + lazy loading:
```bash
# Break video into chunks
ffmpeg -i video.mp4 -c:v libx264 -c:a aac -hls_time 10 -hls_list_size 0 output.m3u8

# React video.js loads chunks on demand
```

**Performance impact:** Minimal (only load visible segments)

---

## Q: Can users collaborate on editing?

**A:** Yes, using WebSocket in `caption_editor_api.py`:
```python
@app.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    # Real-time sync between users
```

**Future feature** for Phase 2+

---

## Q: How do I store this in a database?

**A:** Replace JSON files with SQL:
```sql
CREATE TABLE caption_projects (...);
CREATE TABLE caption_segments (...);
```

Replace file I/O in `CaptionProject.save_to_file()` with DB operations.

**Current approach (JSON):** Fine for MVP, scales to ~1000 projects

---

## Q: What about versioning/undo?

**A:** Add version history:
```python
@dataclass
class CaptionProject:
    versions: List[Dict]  # Store each save
    version_index: int = 0  # Current version
    
    def undo(self):
        if self.version_index > 0:
            self.version_index -= 1
    
    def redo(self):
        if self.version_index < len(self.versions) - 1:
            self.version_index += 1
```

**Future enhancement** for Phase 3+

---

## Q: How do I optimize rendering?

**A:** Layer approach:
1. **Preview**: ASS subtitles (fast, ~2s for 10s video)
2. **Export**: TextClips (high quality, ~5min for full video)

Use existing `app/burner.py` logic with edited captions.

---

## Q: What if FFmpeg isn't installed?

**A:** The file validator already checks:
```python
# app/file_validator.py handles missing ffmpeg gracefully
# app/audio.py raises helpful error messages
```

Just ensure ffmpeg is on PATH in production.

---

## Quick Debug Checklist

**Backend not responding?**
```bash
# Check FastAPI is running
curl http://localhost:8000/docs

# Check CORS configuration
# Verify allowed_origins includes React URL
```

**React can't call API?**
```bash
# Check REACT_APP_API_URL environment variable
echo $REACT_APP_API_URL

# Should be http://localhost:8000/api
```

**Video won't play?**
```bash
# Check video path in project
curl http://localhost:8000/api/projects/{project_id} | grep video

# Verify file exists and is readable
ls -lh /path/to/video
```

**Captions not showing?**
```bash
# Check segment times overlap with video duration
# Verify start_time < end_time
# Check font_size > 0

# Render test ASS file
from app.ass_generator import ASSGenerator
ASSGenerator.save_ass_file(project, Path("test.ass"))
# View in text editor to verify format
```

---

## API Endpoint Cheat Sheet

```bash
# Create project
POST /api/projects
  job_id, username, video_filename, transcript

# Get project
GET /api/projects/{project_id}

# List projects
GET /api/projects?username=user

# Update segment
PUT /api/projects/{project_id}/segments/{segment_id}
  {text, start_time, end_time, emphasized}

# Update style
PUT /api/projects/{project_id}/style
  {font_size, font_color, position_x, position_y}

# Toggle sync mode
PUT /api/projects/{project_id}/sync-mode
  {sync_mode: true/false}

# Generate preview
POST /api/projects/{project_id}/preview

# Export final video
POST /api/projects/{project_id}/export
```

---

## File Organization

```
autocaptionsmvp/
├── app/
│   ├── caption_editor.py          ✅ Data models
│   ├── caption_editor_api.py      ✅ FastAPI endpoints
│   ├── ass_generator.py           ✅ ASS rendering
│   ├── burner.py                  ✅ Existing (adapt for projects)
│   └── ...
├── interfaces/
│   └── streamlit_app.py           (Add "Edit Captions" button)
├── caption-editor/                (NEW React app)
│   ├── src/
│   │   ├── components/
│   │   ├── api/
│   │   └── hooks/
│   └── package.json
├── CAPTION_EDITOR_ARCHITECTURE.md ✅ Design
├── CAPTION_EDITOR_REACT_COMPONENTS.tsx ✅ React code
└── CAPTION_EDITOR_IMPLEMENTATION_GUIDE.md ✅ Step-by-step
```

---

## Success Metrics

**When you've succeeded:**
- ✅ Can create/load caption projects
- ✅ Video plays with caption overlay
- ✅ Can edit caption text and timing
- ✅ Changes sync to preview in <500ms
- ✅ Can adjust global style
- ✅ Can export final video with edits
- ✅ Can handle 100+ segments without lag
- ✅ UI feels responsive and smooth

---

## Estimated Costs

| Resource | Estimate |
|----------|----------|
| Development Time | 7-10 days |
| Complexity | Medium-High |
| NPM Dependencies | ~30 packages |
| Server Resources | 4GB RAM (dev), 8GB (production) |
| Deployment | Docker + nginx |

---

## Recommended Tech Stack

**Why this stack?**
- **React**: Industry standard, smooth real-time UI
- **FastAPI**: Fast, modern Python, auto-documentation
- **ASS format**: Lightweight, supports all needed features
- **FFmpeg**: Already in use, battle-tested
- **JSON (MVP)**: Simple, no database setup
- **SQLite/PostgreSQL (later)**: For scaling

---

## Support Resources

- FastAPI docs: https://fastapi.tiangolo.com
- React docs: https://react.dev
- FFmpeg docs: https://ffmpeg.org/ffmpeg.html
- ASS format: https://en.wikipedia.org/wiki/Advanced_SubStation_Alpha

---

## Next Immediate Steps

1. **Review** the 3 main files you created:
   - `app/caption_editor.py`
   - `app/caption_editor_api.py`
   - `app/ass_generator.py`

2. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn
   ```

3. **Test FastAPI:**
   ```bash
   uvicorn app.caption_editor_api:app --reload
   # Visit http://localhost:8000/docs
   ```

4. **Start React project:**
   ```bash
   npx create-react-app caption-editor
   ```

5. **Pick a phase** and commit to it!

---

**Good luck! You've got a solid foundation to build something amazing.** 🚀
