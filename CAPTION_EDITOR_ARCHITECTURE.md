# CapCut-Like Caption Editor - Architecture & Implementation Guide

## Table of Contents
1. [High-Level Architecture](#architecture)
2. [Tech Stack Comparison](#tech-stack)
3. [Data Structures](#data-structures)
4. [Implementation Roadmap](#roadmap)
5. [Code Examples](#code-examples)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CAPTION EDITOR SYSTEM                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐      ┌──────────────┐      ┌─────────────┐ │
│  │   Frontend  │◄────►│   Backend    │◄────►│  Storage    │ │
│  │   (React)   │      │  (FastAPI)   │      │  (JSON)     │ │
│  └─────────────┘      └──────────────┘      └─────────────┘ │
│        ▲                     ▲                                │
│        │                     │                                │
│   Video Preview      Caption Processing                      │
│   Timeline Editor    & Rendering                             │
│   Real-time Sync                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. **Frontend Layer** (React-based for real-time preview)
- **Video Player** (react-player): Display video with overlaid captions
- **Caption Timeline**: Horizontal timeline showing segments
- **Caption Editor**: Text input, timing controls
- **Style Panel**: Global + per-caption styling
- **Real-time Preview**: Updates as user edits

#### 2. **Backend Layer** (FastAPI/Streamlit extension)
- **Project Manager**: CRUD operations on caption projects
- **Caption Processor**: Convert captions to various formats
- **Renderer**: Generate final video with FFmpeg
- **Sync Engine**: Handle real-time updates

#### 3. **Storage Layer**
- **Project Files**: JSON format with all edits
- **Cache**: Processed captions for quick preview
- **Exports**: Final rendered videos

---

## Tech Stack Comparison

### Option 1: Streamlit + HTML5 (Simpler, stays Python)
**Pros:**
- Easy to integrate with existing Streamlit app
- No new backend needed
- Quick to implement

**Cons:**
- Limited real-time interactivity
- Hard to build smooth timeline editor
- Video preview overlay is janky

**Tech:**
- `streamlit-player` for video
- `streamlit_timeline` or custom HTML
- Canvas overlay for captions

---

### Option 2: React Frontend + FastAPI Backend (Recommended)
**Pros:**
- True real-time preview (60fps smooth)
- Professional timeline editor (like Premiere, CapCut)
- Better UX and performance
- Scalable architecture

**Cons:**
- Requires separate frontend
- More complex deployment
- Separate tech stacks (Python + Node)

**Tech:**
- **Frontend**: React, Zustand (state), Tailwind CSS
- **Video**: `video.js` or `HLS.js`
- **Timeline**: `react-timeline-editor` or custom
- **Backend**: FastAPI with WebSocket for real-time sync
- **Rendering**: FFmpeg (existing)

---

### Option 3: Hybrid (Recommended for MVP)
**Use existing Streamlit** for:
- Project management
- Initial caption generation
- Final export

**Use separate lightweight React page** for:
- Caption editing UI
- Real-time preview
- Timing adjustments

**Connection**: REST API (FastAPI) between Streamlit and React

---

## Data Structures

### Caption Project JSON
```json
{
  "project_id": "proj_abc123",
  "job_id": "job_xyz789",
  "username": "user@example.com",
  "video_filename": "video.mp4",
  "sync_mode": true,
  "segments": [
    {
      "id": "seg_001",
      "text": "Hello world",
      "start_time": 0.0,
      "end_time": 2.5,
      "emphasized": true,
      "style_override": null
    }
  ],
  "global_style": {
    "font_name": "Arial",
    "font_size": 110,
    "font_color": "#00FFFF",
    "position_x": 0.5,
    "position_y": 0.8,
    "style_preset": "classic"
  }
}
```

See `app/caption_editor.py` for complete dataclass definitions.

---

## Implementation Roadmap

### Phase 1: Backend (2-3 days)
1. ✓ Caption data models (`caption_editor.py`)
2. Create FastAPI service for CRUD operations
3. Implement project persistence
4. Add caption-to-ASS conversion with edit support

### Phase 2: React Frontend (3-5 days)
1. Basic video player with HLS streaming
2. Caption timeline (simple list first)
3. Caption edit dialog (text + timing)
4. Style panel (global controls)
5. Real-time preview integration

### Phase 3: Integration (2-3 days)
1. Add "Edit Captions" button to Streamlit
2. Launch React editor in modal or new tab
3. Handle save/export from editor
4. Final video generation with edited captions

### Phase 4: Polish (2-3 days)
1. Performance optimization
2. UI refinement
3. Error handling
4. Testing

---

## Implementation Examples

See separate code examples below for:
1. Backend API (FastAPI)
2. React Components (Video Player, Timeline, Editor)
3. ASS subtitle generation with edits
4. Performance optimization

