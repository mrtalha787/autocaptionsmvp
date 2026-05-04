"""
Caption Editor - Data Structures and Models

Handles caption data serialization, validation, and transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
from pathlib import Path
import json
from datetime import timedelta


@dataclass
class CaptionStyle:
    """Individual caption style overrides."""
    font_size: Optional[int] = None
    font_color: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    bg_color: Optional[str] = None
    use_outline: Optional[bool] = None


@dataclass
class CaptionSegment:
    """Single caption segment with timing and style."""
    id: str  # Unique identifier (UUID)
    text: str
    start_time: float  # in seconds
    end_time: float  # in seconds
    emphasized: bool = False
    style_override: Optional[CaptionStyle] = field(default_factory=CaptionStyle)
    
    @property
    def duration(self) -> float:
        """Duration of caption in seconds."""
        return self.end_time - self.start_time
    
    @duration.setter
    def duration(self, value: float):
        """Set duration by adjusting end time."""
        self.end_time = self.start_time + value
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "emphasized": self.emphasized,
            "style_override": asdict(self.style_override) if self.style_override else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> CaptionSegment:
        """Create from dictionary."""
        style_data = data.get("style_override")
        style = CaptionStyle(**style_data) if style_data else None
        return cls(
            id=data["id"],
            text=data["text"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            emphasized=data.get("emphasized", False),
            style_override=style,
        )


@dataclass
class GlobalCaptionStyle:
    """Global styling applied to all captions."""
    font_name: str = "Arial"
    font_size: int = 110
    font_color: str = "#00FFFF"
    position_x: float = 0.5
    position_y: float = 0.5
    bg_color: str = "#000000"
    bg_opacity: float = 0.7
    outline_width: int = 2
    outline_color: str = "#000000"
    style_preset: str = "classic"  # classic, bold, outlined
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> GlobalCaptionStyle:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CaptionProject:
    """Complete caption editing project."""
    project_id: str
    job_id: str
    username: str
    video_filename: str
    segments: List[CaptionSegment] = field(default_factory=list)
    global_style: GlobalCaptionStyle = field(default_factory=GlobalCaptionStyle)
    sync_mode: bool = True  # If True, all captions use global style
    created_at: float = field(default_factory=lambda: __import__('time').time())
    last_modified: float = field(default_factory=lambda: __import__('time').time())
    transcript: str = ""
    
    def to_dict(self) -> Dict:
        """Convert entire project to dictionary."""
        return {
            "project_id": self.project_id,
            "job_id": self.job_id,
            "username": self.username,
            "video_filename": self.video_filename,
            "segments": [seg.to_dict() for seg in self.segments],
            "global_style": self.global_style.to_dict(),
            "sync_mode": self.sync_mode,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "transcript": self.transcript,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> CaptionProject:
        """Create from dictionary."""
        return cls(
            project_id=data["project_id"],
            job_id=data["job_id"],
            username=data["username"],
            video_filename=data["video_filename"],
            segments=[CaptionSegment.from_dict(seg) for seg in data.get("segments", [])],
            global_style=GlobalCaptionStyle.from_dict(data.get("global_style", {})),
            sync_mode=data.get("sync_mode", True),
            created_at=data.get("created_at", __import__('time').time()),
            last_modified=data.get("last_modified", __import__('time').time()),
            transcript=data.get("transcript", ""),
        )
    
    def save_to_file(self, file_path: str | Path) -> None:
        """Save project to JSON file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str | Path) -> CaptionProject:
        """Load project from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_effective_style(self, segment_id: Optional[str] = None) -> Dict:
        """
        Get effective style for a segment (merged global + override).
        
        Args:
            segment_id: If provided, merge segment's style override with global style
            
        Returns:
            Dictionary of style properties
        """
        style = self.global_style.to_dict()
        
        if segment_id and not self.sync_mode:
            # Find segment and apply overrides
            for seg in self.segments:
                if seg.id == segment_id and seg.style_override:
                    for key, value in asdict(seg.style_override).items():
                        if value is not None:
                            style[key] = value
                    break
        
        return style


# Example JSON structure
EXAMPLE_PROJECT_JSON = """
{
  "project_id": "proj_123456",
  "job_id": "job_abc123",
  "username": "john_doe",
  "video_filename": "my_video.mp4",
  "sync_mode": true,
  "transcript": "Hello world this is a test video",
  "global_style": {
    "font_name": "Arial",
    "font_size": 110,
    "font_color": "#00FFFF",
    "position_x": 0.5,
    "position_y": 0.8,
    "bg_color": "#000000",
    "bg_opacity": 0.7,
    "outline_width": 2,
    "outline_color": "#000000",
    "style_preset": "classic"
  },
  "segments": [
    {
      "id": "seg_001",
      "text": "Hello world",
      "start_time": 0.0,
      "end_time": 2.5,
      "emphasized": true,
      "style_override": null
    },
    {
      "id": "seg_002",
      "text": "this is a test",
      "start_time": 2.5,
      "end_time": 5.0,
      "emphasized": false,
      "style_override": {
        "font_size": 120,
        "font_color": "#FF00FF",
        "position_x": null,
        "position_y": null,
        "bg_color": null,
        "use_outline": true
      }
    }
  ],
  "created_at": 1714920000.0,
  "last_modified": 1714920000.0
}
"""


def create_project_from_job(job_id: str, username: str, video_filename: str, 
                           transcript: str, segments_data: List[Dict]) -> CaptionProject:
    """
    Create a new caption project from a processed job.
    
    Args:
        job_id: ID of the original processing job
        username: Username who owns the project
        video_filename: Name of the video file
        transcript: Full transcript text
        segments_data: List of caption segments from transcription
        
    Returns:
        CaptionProject instance
    """
    import uuid
    
    project = CaptionProject(
        project_id=f"proj_{uuid.uuid4().hex[:12]}",
        job_id=job_id,
        username=username,
        video_filename=video_filename,
        transcript=transcript,
    )
    
    # Create segments from transcription
    for idx, seg in enumerate(segments_data):
        project.segments.append(
            CaptionSegment(
                id=f"seg_{idx:03d}",
                text=seg.get("text", ""),
                start_time=float(seg.get("start", 0)),
                end_time=float(seg.get("end", 0)),
                emphasized=seg.get("emphasized", False),
            )
        )
    
    return project
