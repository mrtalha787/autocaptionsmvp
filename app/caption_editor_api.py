"""
Backend API for Caption Editor - FastAPI endpoints

This handles CRUD operations for caption projects and real-time sync.
Integration point between Streamlit, React frontend, and caption processing.
"""

from fastapi import FastAPI, HTTPException, WebSocket, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import uuid
from pathlib import Path

from app.caption_editor import CaptionProject, CaptionSegment, GlobalCaptionStyle

# Initialize FastAPI app
app = FastAPI(title="Caption Editor API")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
PROJECTS_DIR = Path("storage/caption_projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Pydantic Models (for request/response validation)
# ============================================================================

class CaptionSegmentUpdate(BaseModel):
    """Request model for updating a caption segment."""
    text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    emphasized: Optional[bool] = None
    style_override: Optional[dict] = None


class GlobalStyleUpdate(BaseModel):
    """Request model for updating global caption style."""
    font_name: Optional[str] = None
    font_size: Optional[int] = None
    font_color: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    style_preset: Optional[str] = None


class ProjectResponse(BaseModel):
    """Response model for project data."""
    project_id: str
    job_id: str
    username: str
    video_filename: str
    sync_mode: bool
    segment_count: int
    last_modified: float


# ============================================================================
# Project Management Endpoints
# ============================================================================

@app.post("/api/projects")
async def create_project(
    job_id: str,
    username: str,
    video_filename: str,
    transcript: str = "",
):
    """Create a new caption editing project from a processed job."""
    try:
        project = CaptionProject(
            project_id=f"proj_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            username=username,
            video_filename=video_filename,
            transcript=transcript,
        )
        
        # Save project
        project_file = PROJECTS_DIR / f"{project.project_id}.json"
        project.save_to_file(project_file)
        
        return {
            "status": "success",
            "project_id": project.project_id,
            "message": "Project created successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Retrieve a caption project."""
    try:
        project_file = PROJECTS_DIR / f"{project_id}.json"
        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = CaptionProject.load_from_file(project_file)
        return project.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects")
async def list_projects(username: str):
    """List all projects for a user."""
    try:
        projects = []
        for project_file in PROJECTS_DIR.glob("*.json"):
            project = CaptionProject.load_from_file(project_file)
            if project.username == username:
                projects.append({
                    "project_id": project.project_id,
                    "job_id": project.job_id,
                    "video_filename": project.video_filename,
                    "segment_count": len(project.segments),
                    "last_modified": project.last_modified,
                    "sync_mode": project.sync_mode,
                })
        
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Caption Segment Endpoints
# ============================================================================

@app.post("/api/projects/{project_id}/segments")
async def add_segment(project_id: str, segment: CaptionSegmentUpdate):
    """Add a new caption segment to project."""
    try:
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        # Create new segment
        new_segment = CaptionSegment(
            id=f"seg_{len(project.segments):03d}",
            text=segment.text or "",
            start_time=segment.start_time or 0,
            end_time=segment.end_time or 5,
        )
        
        project.segments.append(new_segment)
        project.save_to_file(project_file)
        
        return {"status": "success", "segment_id": new_segment.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/projects/{project_id}/segments/{segment_id}")
async def update_segment(
    project_id: str,
    segment_id: str,
    update: CaptionSegmentUpdate,
):
    """Update a caption segment."""
    try:
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        # Find and update segment
        for seg in project.segments:
            if seg.id == segment_id:
                if update.text is not None:
                    seg.text = update.text
                if update.start_time is not None:
                    seg.start_time = update.start_time
                if update.end_time is not None:
                    seg.end_time = update.end_time
                if update.emphasized is not None:
                    seg.emphasized = update.emphasized
                
                project.last_modified = __import__('time').time()
                project.save_to_file(project_file)
                
                return {"status": "success", "segment": seg.to_dict()}
        
        raise HTTPException(status_code=404, detail="Segment not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/projects/{project_id}/segments/{segment_id}")
async def delete_segment(project_id: str, segment_id: str):
    """Delete a caption segment."""
    try:
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        project.segments = [s for s in project.segments if s.id != segment_id]
        project.save_to_file(project_file)
        
        return {"status": "success", "message": "Segment deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Style Endpoints
# ============================================================================

@app.put("/api/projects/{project_id}/style")
async def update_global_style(project_id: str, style: GlobalStyleUpdate):
    """Update global caption style."""
    try:
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        # Update style fields
        update_dict = style.dict(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(project.global_style, key):
                setattr(project.global_style, key, value)
        
        project.save_to_file(project_file)
        
        return {"status": "success", "style": project.global_style.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/projects/{project_id}/sync-mode")
async def toggle_sync_mode(project_id: str, sync_mode: bool):
    """Toggle sync mode on/off."""
    try:
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        project.sync_mode = sync_mode
        project.save_to_file(project_file)
        
        return {"status": "success", "sync_mode": project.sync_mode}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Preview & Rendering Endpoints
# ============================================================================

@app.post("/api/projects/{project_id}/preview")
async def generate_preview(project_id: str, duration: int = 10):
    """
    Generate a short preview video with current captions.
    
    Args:
        project_id: Project ID
        duration: Duration of preview in seconds (for performance)
    
    Returns:
        Preview video URL or path
    """
    try:
        from app.burner import render_captions
        
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        # Convert segments to caption format expected by burner
        captions = [
            {
                "text": seg.text,
                "start": seg.start_time,
                "end": seg.end_time,
                "emphasized": seg.emphasized,
            }
            for seg in project.segments
            if seg.start_time < duration
        ]
        
        # Get effective style
        style = project.get_effective_style()
        
        # Render preview video
        output_path = Path(f"storage/previews/{project_id}_preview.mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = render_captions(
            video_path=project.video_filename,
            captions=captions,
            output_path=output_path,
            pos_x=style["position_x"],
            pos_y=style["position_y"],
            font_name=style["font_name"],
            font_size=style["font_size"],
            font_color=style["font_color"],
        )
        
        return {
            "status": "success",
            "preview_url": f"/api/preview/{project_id}",
            "duration": result["burn_seconds"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/projects/{project_id}/export")
async def export_final_video(project_id: str):
    """
    Generate final video with all edited captions.
    
    Returns:
        Final video path or download URL
    """
    try:
        from app.burner import render_captions
        
        project_file = PROJECTS_DIR / f"{project_id}.json"
        project = CaptionProject.load_from_file(project_file)
        
        # Convert segments to caption format
        captions = [seg.to_dict() for seg in project.segments]
        
        # Get effective style
        style = project.get_effective_style()
        
        # Render final video
        output_path = Path(f"storage/outputs/{project_id}_final.mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = render_captions(
            video_path=project.video_filename,
            captions=captions,
            output_path=output_path,
            pos_x=style["position_x"],
            pos_y=style["position_y"],
            font_name=style["font_name"],
            font_size=style["font_size"],
            font_color=style["font_color"],
            fast_mode=False,  # Use high quality for final export
        )
        
        return {
            "status": "success",
            "output_path": str(output_path),
            "download_url": f"/api/download/{project_id}",
            "duration": result["burn_seconds"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# WebSocket for Real-time Sync (Optional, Advanced)
# ============================================================================

@app.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time project updates.
    
    Useful for:
    - Multi-user collaboration (if needed in future)
    - Real-time preview updates
    - Live sync between multiple editor instances
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "segment_update":
                # Apply update and broadcast
                project_file = PROJECTS_DIR / f"{project_id}.json"
                project = CaptionProject.load_from_file(project_file)
                
                # Update segment
                for seg in project.segments:
                    if seg.id == data.get("segment_id"):
                        if "text" in data:
                            seg.text = data["text"]
                        if "start_time" in data:
                            seg.start_time = data["start_time"]
                        if "end_time" in data:
                            seg.end_time = data["end_time"]
                
                project.save_to_file(project_file)
                
                # Broadcast update
                await websocket.send_json({
                    "type": "update_ack",
                    "segment_id": data.get("segment_id"),
                    "status": "success",
                })
    
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
