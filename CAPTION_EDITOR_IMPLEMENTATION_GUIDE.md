# Caption Editor - Complete Implementation Guide

## Quick Start

This document guides you through implementing the CapCut-like caption editing system.

**Estimated Timeline:** 7-10 days of development
**Complexity:** Medium-High
**Tech Stack:** Python (FastAPI) + React + FFmpeg

---

## Architecture Summary

```
Streamlit App (Main Entry Point)
    ↓
    ├─→ Process video → Generate captions
    ├─→ "Edit Captions" button → Open React editor
    └─→ Editor saves changes → Render final video
         ↓
      FastAPI Backend (REST API)
         ↓
      React Frontend (Real-time editor)
         ↓
      Caption Project (JSON storage)
```

---

## Implementation Phases

### Phase 1: Backend Setup (Days 1-2)

**Goal:** Create API endpoints for caption management

**Files to create/modify:**
- ✅ `app/caption_editor.py` - Data models (DONE)
- ✅ `app/caption_editor_api.py` - FastAPI endpoints (DONE)
- ✅ `app/ass_generator.py` - ASS subtitle generation (DONE)
- Create: `app/caption_renderer.py` - Video rendering with edited captions

**Steps:**

1. **Install FastAPI**
```bash
pip install fastapi uvicorn python-multipart
```

2. **Run the API**
```bash
uvicorn app.caption_editor_api:app --reload --port 8000
```

3. **Test endpoints**
```bash
# Create project
curl -X POST http://localhost:8000/api/projects \
  -d "job_id=job_123&username=user&video_filename=video.mp4"

# Get project
curl http://localhost:8000/api/projects/proj_abc123
```

4. **Update ASS renderer** in `app/burner.py` to use edited captions:

```python
# In render_captions function, add support for edited caption projects
if isinstance(captions, CaptionProject):
    # Use project's edited segments instead of original
    captions = project.segments
```

---

### Phase 2: React Frontend Setup (Days 3-5)

**Goal:** Build interactive caption editing UI

**Create React app:**
```bash
# Create new React project in separate directory
npx create-react-app caption-editor
cd caption-editor
npm install axios zustand hls.js tailwindcss
```

**Project structure:**
```
caption-editor/
├── src/
│   ├── components/
│   │   ├── VideoPlayer.tsx
│   │   ├── Timeline.tsx
│   │   ├── CaptionEditor.tsx
│   │   ├── StyleControls.tsx
│   │   └── CaptionEditorApp.tsx
│   ├── hooks/
│   │   ├── useProject.ts
│   │   └── useVideo.ts
│   ├── types/
│   │   └── caption.ts
│   ├── api/
│   │   └── client.ts
│   ├── App.tsx
│   └── index.css
└── package.json
```

**Key files to create:**

1. **`src/api/client.ts`** - API communication
```typescript
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const api = {
  getProject: (projectId: string) =>
    fetch(`${API_BASE}/projects/${projectId}`).then(r => r.json()),
  
  updateSegment: (projectId: string, segmentId: string, updates: any) =>
    fetch(`${API_BASE}/projects/${projectId}/segments/${segmentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    }).then(r => r.json()),
  
  updateStyle: (projectId: string, style: any) =>
    fetch(`${API_BASE}/projects/${projectId}/style`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(style)
    }).then(r => r.json()),
  
  exportVideo: (projectId: string) =>
    fetch(`${API_BASE}/projects/${projectId}/export`, {
      method: 'POST'
    }).then(r => r.json()),
};
```

2. **`src/hooks/useProject.ts`** - State management
```typescript
import { useState, useEffect } from 'react';
import { api } from '../api/client';

export const useProject = (projectId: string) => {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProject(projectId).then(data => {
      setProject(data);
      setLoading(false);
    });
  }, [projectId]);

  const updateSegment = (segmentId: string, updates: any) => {
    return api.updateSegment(projectId, segmentId, updates)
      .then(() => {
        // Refresh project
        return api.getProject(projectId).then(data => {
          setProject(data);
        });
      });
  };

  return { project, loading, updateSegment };
};
```

3. **Setup CORS in FastAPI** (`app/caption_editor_api.py`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",   # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Phase 3: Integration with Streamlit (Days 6-7)

**Goal:** Connect React editor to Streamlit workflow

**Modify `interfaces/streamlit_app.py`:**

```python
# Add import
from app.caption_editor import CaptionProject, create_project_from_job

# After processing a job, add "Edit Captions" button
if job["status"] == "done":
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="⬇️ Download video",
            data=...,
            file_name=...,
        )
    
    with col2:
        if st.button("✏️ Edit Captions (Advanced)"):
            # Create caption project
            project = create_project_from_job(
                job_id=job["job_id"],
                username=st.session_state.username,
                video_filename=job["filename"],
                transcript=job.get("transcript", ""),
                segments_data=job.get("captions", []),  # From transcription
            )
            project.save_to_file(...)
            
            st.info(f"""
                Caption editor opened!
                Project ID: {project.project_id}
                Open editor: http://localhost:3000?project={project.project_id}
            """)
```

---

### Phase 4: Performance Optimization (Days 8-9)

**Optimize video preview:**

1. **Generate HLS stream** for efficient video streaming
```bash
ffmpeg -i video.mp4 -c:v libx264 -c:a aac -hls_time 10 -hls_list_size 0 -f hls output.m3u8
```

2. **Thumbnail generation** for timeline preview
```python
# Generate frame at specific timestamp
subprocess.run([
    'ffmpeg', '-i', video_path,
    '-ss', str(timestamp),
    '-vframes', '1',
    '-vf', 'scale=80:-1',
    thumbnail_path
])
```

3. **Cache rendered previews**
```python
@lru_cache(maxsize=100)
def get_preview_at_time(project_id, timestamp):
    # Render caption at specific time
    pass
```

---

### Phase 5: Polish & Testing (Days 10+)

**Testing checklist:**
- [ ] All API endpoints functional
- [ ] Video plays smoothly with caption overlay
- [ ] Timeline drag/drop works
- [ ] Caption edits save correctly
- [ ] Export generates valid video
- [ ] Handles large videos (>1GB)
- [ ] Performance acceptable (<2s caption update)

**UI Polish:**
- [ ] Keyboard shortcuts (↑↓ for prev/next segment, Space for play)
- [ ] Undo/redo functionality
- [ ] Loading indicators
- [ ] Error handling and user feedback
- [ ] Mobile responsiveness (if needed)

---

## Feature Prioritization

### MVP (Must Have)
1. Video player with caption overlay
2. Edit caption text and timing
3. Timeline scrubbing
4. Global style controls
5. Export final video

### Phase 2 (Nice to Have)
1. Per-caption style overrides
2. Emphasis word highlighting
3. Preview generation
4. Keyboard shortcuts
5. Batch operations

### Future (Enhancements)
1. Multi-user collaboration
2. Caption templates/presets
3. Auto-sync to music beats
4. Advanced effects (blur, highlight, animations)
5. Caption translation/multilingual

---

## Deployment Guide

### Local Development
```bash
# Terminal 1: FastAPI backend
cd /path/to/autocaptionsmvp
uvicorn app.caption_editor_api:app --reload --port 8000

# Terminal 2: React frontend
cd caption-editor
npm start  # Runs on http://localhost:3000

# Terminal 3: Streamlit (existing)
streamlit run interfaces/streamlit_app.py
```

### Production (Docker)

**Backend Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.caption_editor_api:app", "--host", "0.0.0.0"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Troubleshooting

### CORS Errors
**Problem:** React can't reach FastAPI endpoints
**Solution:** 
- Check CORS is configured in `caption_editor_api.py`
- Verify both servers are running
- Check browser console for exact error

### Video won't play
**Problem:** HLS stream not loading
**Solution:**
- Verify ffmpeg installed: `ffmpeg -version`
- Check video path is correct
- Try direct file serving instead of HLS first

### Caption timing off
**Problem:** Captions appear at wrong times
**Solution:**
- Verify video duration is correct
- Check segment timestamps in project JSON
- Ensure FFmpeg gets correct duration

---

## Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Load project | <500ms | ? |
| Update segment | <200ms | ? |
| Render preview (10s) | <2s | ? |
| Export full video | <5min | ? |
| Handle 100+ segments | <1s | ? |

---

## Database (Optional Future)

When scaling, replace JSON files with database:

```sql
-- Projects table
CREATE TABLE caption_projects (
  id VARCHAR(255) PRIMARY KEY,
  job_id VARCHAR(255),
  username VARCHAR(255),
  video_filename VARCHAR(255),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Segments table  
CREATE TABLE caption_segments (
  id VARCHAR(255) PRIMARY KEY,
  project_id VARCHAR(255) REFERENCES caption_projects(id),
  text TEXT,
  start_time FLOAT,
  end_time FLOAT,
  emphasized BOOLEAN,
  style_override JSON
);
```

---

## Next Steps

1. **Review** the provided code files
2. **Set up** FastAPI backend and test endpoints
3. **Create** React project and implement components
4. **Test** integration between Streamlit, FastAPI, and React
5. **Iterate** based on feedback and add features

Good luck! 🚀
