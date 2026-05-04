# React Caption Editor - Setup Guide

## Project Structure

You need **TWO separate projects**:

```
C:\dev\
├── autocaptionsmvp/              ← Python Backend (existing)
└── caption-editor/               ← React Frontend (NEW - create this)
```

---

## Step-by-Step Setup

### Step 1: Create React App (OUTSIDE your Python project)

```bash
# Navigate to parent directory
cd C:\dev\

# Create new React app
npx create-react-app caption-editor

# Navigate into it
cd caption-editor
```

### Step 2: Install Dependencies

```bash
npm install axios zustand hls.js
npm install --save-dev @types/hls.js typescript
```

### Step 3: Create Component Files

Create these files in your React project:

**`src/components/VideoPlayer.tsx`**
- Copy the `VideoPlayer` component from `CAPTION_EDITOR_REACT_COMPONENTS.tsx`

**`src/components/Timeline.tsx`**
- Copy the `Timeline` component

**`src/components/CaptionEditor.tsx`**
- Copy the `CaptionEditor` component

**`src/components/StyleControls.tsx`**
- Copy the `StyleControls` component

**`src/components/CaptionEditorApp.tsx`**
- Copy the `CaptionEditorApp` component

**`src/api/client.ts`**
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

### Step 4: Update `src/App.tsx`

```typescript
import React from 'react';
import { CaptionEditorApp } from './components/CaptionEditorApp';
import './App.css';

function App() {
  // Get projectId and videoUrl from URL params or props
  const params = new URLSearchParams(window.location.search);
  const projectId = params.get('project') || 'demo';
  const videoUrl = params.get('video') || 'http://localhost:8000/api/videos/sample.mp4';
  
  return (
    <CaptionEditorApp projectId={projectId} videoUrl={videoUrl} />
  );
}

export default App;
```

### Step 5: Create `.env` File

Create `.env` in the React project root:

```
REACT_APP_API_URL=http://localhost:8000/api
```

### Step 6: Update `tsconfig.json`

Ensure it has proper React settings:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src"],
  "exclude": ["node_modules"]
}
```

---

## Running Both Servers

**Terminal 1: Python Backend**
```bash
cd c:\autocaptionsmvp
# Make sure FastAPI is installed
pip install fastapi uvicorn

# Run the API
uvicorn app.caption_editor_api:app --reload --port 8000
```

**Terminal 2: React Frontend**
```bash
cd c:\dev\caption-editor
npm start
# Opens at http://localhost:3000
```

**Terminal 3: Streamlit (existing)**
```bash
cd c:\autocaptionsmvp
streamlit run interfaces/streamlit_app.py
# Opens at http://localhost:8501
```

---

## File References

| File | Purpose | Location |
|------|---------|----------|
| `CAPTION_EDITOR_REACT_COMPONENTS.tsx` | Reference code | Python project (for reference only) |
| Component files (VideoPlayer.tsx, etc.) | Actual implementation | React project `/src/components/` |
| `caption_editor_api.py` | FastAPI backend | Python project `/app/` |
| `caption_editor.py` | Data models | Python project `/app/` |
| `ass_generator.py` | ASS rendering | Python project `/app/` |

---

## Troubleshooting TypeScript Errors

**Error: "Cannot find module 'react'"**
- Ensure you ran `npm install` in the React project
- Check you're in the correct React project directory

**Error: "JSX element implicitly has type 'any'"**
- You might still be editing the file in the Python project
- The file should be `.tsx` in a React project with `tsconfig.json`

**Error: "CORS error" when calling API**
- Ensure FastAPI backend has CORS enabled (it does in `caption_editor_api.py`)
- Verify the `REACT_APP_API_URL` environment variable is correct

---

## Next Steps

1. ✅ Set up Python backend with FastAPI
2. ✅ Create separate React project
3. ✅ Copy components to React project
4. ✅ Run both servers
5. ✅ Test in browser at http://localhost:3000

---

## Project Directories

After setup, your folder structure should look like:

```
C:\dev\
├── autocaptionsmvp/              (Python - backend)
│   ├── app/
│   │   ├── caption_editor.py ✅
│   │   ├── caption_editor_api.py ✅
│   │   ├── ass_generator.py ✅
│   │   └── ...
│   ├── interfaces/
│   ├── CAPTION_EDITOR_REACT_COMPONENTS.tsx (reference only)
│   └── ...
│
└── caption-editor/               (React - frontend, NEW)
    ├── src/
    │   ├── components/
    │   │   ├── VideoPlayer.tsx ← Copy from reference file
    │   │   ├── Timeline.tsx ← Copy from reference file
    │   │   ├── CaptionEditor.tsx ← Copy from reference file
    │   │   ├── StyleControls.tsx ← Copy from reference file
    │   │   └── CaptionEditorApp.tsx ← Copy from reference file
    │   ├── api/
    │   │   └── client.ts
    │   ├── App.tsx
    │   └── index.tsx
    ├── public/
    ├── .env
    ├── package.json
    ├── tsconfig.json
    └── ...
```

---

## Summary

| What | Where | Technology |
|------|-------|-----------|
| Backend API | Python project | FastAPI on :8000 |
| React components | Separate React project | React on :3000 |
| Reference code | Python project (documentation) | TypeScript |
| Data models | Python project | Python dataclasses |
| Rendering | Python project | FFmpeg + ASS |

The React components file in your Python project is just **reference/documentation**. The actual implementation goes in a separate React project.
