"""
ASS Subtitle Generator with Edit Support

Generates ASS subtitle files from edited caption segments.
ASS format is used by FFmpeg for lightweight, fast caption rendering.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from app.caption_editor import CaptionProject, GlobalCaptionStyle


class ASSGenerator:
    """Generates ASS subtitle files from caption projects."""
    
    # Color conversion helpers
    @staticmethod
    def hex_to_bgr(hex_color: str) -> str:
        """
        Convert hex color (#RRGGBB) to BGR format for ASS.
        
        ASS uses BGR format: &HbbGGRR
        """
        hex_color = hex_color.lstrip('#')
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
        return f"&H{b}{g}{r}"
    
    @staticmethod
    def seconds_to_ass_time(seconds: float) -> str:
        """
        Convert seconds to ASS time format: H:MM:SS.CS
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    
    @staticmethod
    def generate_style_line(name: str, style: GlobalCaptionStyle) -> str:
        """Generate ASS Style definition line."""
        # Convert colors
        primary_color = ASSGenerator.hex_to_bgr(style.font_color)
        outline_color = ASSGenerator.hex_to_bgr(style.outline_color)
        back_color = ASSGenerator.hex_to_bgr(style.bg_color)
        
        # Outline width based on preset
        outline_width = {
            "classic": 1,
            "bold": 3,
            "outlined": 2,
        }.get(style.style_preset, 1)
        
        # Shadow offset
        shadow_x = 0
        shadow_y = 0
        
        style_line = (
            f"Style: {name},"
            f"{style.font_name},"  # FontName
            f"{style.font_size},"  # FontSize
            f"&H00FFFFFF,"  # PrimaryColour (white)
            f"&H000000FF,"  # SecondaryColour (red)
            f"{outline_color},"  # OutlineColour
            f"&H00000000,"  # BackColour (black)
            f"0,"  # Bold (0=no, -1=yes)
            f"0,"  # Italic
            f"0,"  # Underline
            f"0,"  # StrikeOut
            f"100,"  # ScaleX
            f"100,"  # ScaleY
            f"0,"  # Spacing
            f"0,"  # Angle
            f"1,"  # BorderStyle
            f"{outline_width},"  # Outline
            f"{shadow_x},"  # Shadow
            f"2,"  # Alignment (2=bottom center)
            f"0,"  # MarginL
            f"0,"  # MarginR
            f"0,"  # MarginV
            f"1,"  # Encoding
        )
        
        return style_line
    
    @classmethod
    def generate_ass_content(cls, project: CaptionProject) -> str:
        """
        Generate complete ASS subtitle file content.
        
        Args:
            project: CaptionProject instance with segments and styles
            
        Returns:
            Complete ASS file content as string
        """
        style = project.global_style
        
        # ASS file header
        ass_content = "[Script Info]\n"
        ass_content += "Title: Auto Captions\n"
        ass_content += "ScriptType: v4.00+\n"
        ass_content += "Collisions: Normal\n"
        ass_content += "PlayResX: 1920\n"
        ass_content += "PlayResY: 1080\n"
        ass_content += "\n"
        
        # V4+ Styles
        ass_content += "[V4+ Styles]\n"
        ass_content += "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        
        # Generate style line
        style_line = cls.generate_style_line("Default", style)
        ass_content += style_line + "\n"
        ass_content += "\n"
        
        # Events (actual captions)
        ass_content += "[Events]\n"
        ass_content += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        
        for segment in project.segments:
            start_time = cls.seconds_to_ass_time(segment.start_time)
            end_time = cls.seconds_to_ass_time(segment.end_time)
            
            # Text with position
            # Position format: {\\pos(x,y)} where x,y are in pixels
            # Calculate position based on percentage
            pos_x = int(1920 * style.position_x)
            pos_y = int(1080 * style.position_y)
            
            # Styling for emphasized words (make them brighter/larger)
            text = segment.text
            if segment.emphasized:
                # Add style tags for emphasis
                text = f"{{\\c&H00FF00FF&}}{text}{{\\c&H00FFFFFF&}}"  # Magenta for emphasized
            
            # Add position
            text = f"{{\\pos({pos_x},{pos_y})}}{text}"
            
            # Create event line
            event_line = (
                f"Dialogue: 0,"
                f"{start_time},"
                f"{end_time},"
                f"Default,,"
                f"0,0,0,,"
                f"{text}"
            )
            
            ass_content += event_line + "\n"
        
        return ass_content
    
    @classmethod
    def save_ass_file(cls, project: CaptionProject, output_path: Path) -> None:
        """
        Generate and save ASS file.
        
        Args:
            project: CaptionProject instance
            output_path: Path where to save the .ass file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = cls.generate_ass_content(project)
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(content)
        
        print(f"[ASS] Generated ASS file: {output_path}")


# Example usage
if __name__ == "__main__":
    from app.caption_editor import CaptionProject, CaptionSegment
    
    # Create example project
    project = CaptionProject(
        project_id="example",
        job_id="job123",
        username="test_user",
        video_filename="test.mp4",
    )
    
    # Add example segments
    project.segments = [
        CaptionSegment(
            id="seg_001",
            text="Hello world",
            start_time=0.0,
            end_time=2.5,
            emphasized=True,
        ),
        CaptionSegment(
            id="seg_002",
            text="Welcome to the tutorial",
            start_time=2.5,
            end_time=5.0,
            emphasized=False,
        ),
    ]
    
    # Generate and save ASS file
    ASSGenerator.save_ass_file(project, Path("test.ass"))
    print("ASS file created: test.ass")
