"""
Caption rendering / burning using MoviePy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import subprocess
import tempfile

from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont, ImageColor
import numpy as np
import time
import gc
from app.ass_renderer import build_ass

# Compatibility for newer Pillow where ANTIALIAS is removed
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

def _parse_color(value):
    if not value:
        return None
    if isinstance(value, tuple):
        return value
    if isinstance(value, str) and value.startswith("rgba"):
        inner = value[value.find("(")+1:value.find(")")]
        parts = [float(x.strip()) for x in inner.split(",")]
        r, g, b, a = parts
        return (int(r), int(g), int(b), int(a * 255 if a <= 1 else a))
    return ImageColor.getrgb(value)

STYLES: Dict[str, Dict] = {
    "hormozi": {
        "font": "Arial-Bold",
        "fontsize": 60,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 3,
        "emph_color": "yellow",
        "emph_size_delta": 6,
        "bg_color": None,
    },
    "elegant": {
        "font": "Helvetica-Narrow",
        "fontsize": 54,
        "color": "#D4AF37",
        "stroke_color": None,
        "stroke_width": 0,
        "emph_color": "#FFD700",
        "emph_size_delta": 4,
        "bg_color": None,
        "shadow": {"offset": (2, 2), "color": (0, 0, 0, 90)},
    },
    "cinematic": {
        "font": "Arial-Bold",
        "fontsize": 58,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 2,
        "emph_color": "white",
        "emph_size_delta": 4,
        "bg_color": (0, 0, 0, int(0.6 * 255)),
        "kerning": 2,
        "animate": True,
        "fade_duration": 0.25,
    },
}

POSITION_MAP = {
    "top-left": ("left", "top"),
    "top": ("center", "top"),
    "top-right": ("right", "top"),
    "center-left": ("left", "center"),
    "center": ("center", "center"),
    "center-right": ("right", "center"),
    "bottom-left": ("left", "bottom"),
    "bottom": ("center", "bottom"),
    "bottom-right": ("right", "bottom"),
}
POSITION_FRACTIONS = {
    "top-left": (0.1, 0.1),
    "top": (0.5, 0.1),
    "top-right": (0.9, 0.1),
    "center-left": (0.1, 0.5),
    "center": (0.5, 0.5),
    "center-right": (0.9, 0.5),
    "bottom-left": (0.1, 0.9),
    "bottom": (0.5, 0.9),
    "bottom-right": (0.9, 0.9),
}


def _load_font(style: Dict, emph: bool = False) -> ImageFont.FreeTypeFont:
    size = style.get("fontsize", 60) + (style.get("emph_size_delta", 0) if emph else 0)
    font_name = style.get("font", "Arial")
    return _font_cached(font_name, size)


@lru_cache(maxsize=64)
def _font_cached(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(font_name, size=size)
    except Exception:
        return ImageFont.truetype("arial.ttf", size=size)


def _render_caption_image(words: List[Dict], style: Dict, max_width: int) -> Image.Image:
    base_font = _load_font(style, emph=False)
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    space_w = draw.textbbox((0, 0), " ", font=base_font)[2]
    kerning = style.get("kerning", 4)

    # Build wrapped lines; emphasized words get their own line.
    lines: List[List[Dict]] = []
    current: List[Dict] = []
    current_w = 0
    for w in words:
        font = _load_font(style, emph=w.get("emphasized"))
        bbox = draw.textbbox((0, 0), w["word"], font=font)
        w_width = bbox[2] - bbox[0]

        # force emphasized word onto its own line
        if w.get("emphasized") and current:
            lines.append(current)
            current = []
            current_w = 0

        extra_space = (space_w + kerning) if current else 0
        if current and (current_w + extra_space + w_width) > max_width:
            lines.append(current)
            current = []
            current_w = 0

        current.append({**w, "width": w_width, "font": font})
        current_w += extra_space + w_width

        if w.get("emphasized"):
            lines.append(current)
            current = []
            current_w = 0

    if current:
        lines.append(current)

    # measure lines
    line_heights = []
    line_widths = []
    for line in lines:
        h = max(draw.textbbox((0, 0), w["word"], font=w["font"])[3] for w in line)
        width_accum = 0
        for idx, w in enumerate(line):
            width_accum += w["width"]
            if idx < len(line) - 1:
                width_accum += space_w + kerning
        line_heights.append(h)
        line_widths.append(width_accum)

    padding_x = 40 if style.get("bg_color") else 16
    padding_y = 28
    canvas_w = min(max(line_widths) + padding_x, max_width)
    canvas_h = sum(line_heights) + padding_y + (len(lines) - 1) * 6
    bg = _parse_color(style.get("bg_color"))
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0) if bg is None else bg)
    draw = ImageDraw.Draw(img)

    y_cursor = padding_y // 2
    for line_idx, line in enumerate(lines):
        line_h = line_heights[line_idx]
        line_w = line_widths[line_idx]
        x_cursor = max((canvas_w - line_w) // 2, padding_x // 2)
        for idx, w in enumerate(line):
            font = w["font"]
            word_text = w["word"]
            color = style.get("emph_color") if w.get("emphasized") else style.get("color")
            shadow_cfg = style.get("shadow")
            if shadow_cfg:
                dx, dy = shadow_cfg.get("offset", (2, 2))
                shadow_color = _parse_color(shadow_cfg.get("color", (0, 0, 0, 80)))
                draw.text((x_cursor + dx, y_cursor + dy), word_text, font=font, fill=shadow_color)
            stroke_width = style.get("stroke_width", 0)
            stroke_color = style.get("stroke_color")
            draw.text(
                (x_cursor, y_cursor),
                word_text,
                font=font,
                fill=color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color,
            )
            if idx < len(line) - 1:
                x_cursor += w["width"] + space_w + kerning
            else:
                x_cursor += w["width"]
        y_cursor += line_h + 6

    return img


def render_captions(
    video_path: str | Path,
    captions: List[Dict],
    style_key: str,
    output_path: str | Path,
    position: str | None = None,
    position_xy: tuple[float, float] | None = None,
    fast: bool = True,
    target_width: int = 960,
    mode: str = "moviepy",  # moviepy | ffmpeg
) -> Dict:
    """
    Burn captions onto video. Emphasized words are styled inline (color/size).
    Returns dict with output path and duration seconds.
    """
    started_at = time.perf_counter()
    style = STYLES.get(style_key, STYLES["hormozi"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "ffmpeg":
        # Build ASS and run ffmpeg once (no fallback if it fails)
        with tempfile.TemporaryDirectory() as td:
            ass_path = Path(td) / "captions.ass"
            build_ass(captions, style_key, ass_path)
            vf_parts = []
            if fast:
                vf_parts.append("scale='min(1280,iw)':-2")
            vf_parts.append(f"subtitles=filename='{ass_path.as_posix()}'")
            vf = ",".join(vf_parts)
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast" if fast else "medium",
                "-crf",
                "18",
                "-c:a",
                "copy",
                str(output_path),
            ]
            print("FFmpeg cmd:", " ".join(cmd))
            res = subprocess.run(cmd, check=True)
            duration = time.perf_counter() - started_at
            return {"output_path": output_path, "burn_seconds": duration}

    # moviepy path (fallback)
    if position_xy:
        pos_tuple = position_xy
    elif position:
        pos_tuple = POSITION_FRACTIONS.get(position, (0.5, 0.9))
    else:
        pos_tuple = (0.5, 0.9)
    video = VideoFileClip(str(video_path))
    if fast and video.w > target_width:
        video = video.resize(width=target_width)
    text_clips = []

    max_w = int(video.w * 0.9)
    cpu_threads = max(2, min(8, multiprocessing.cpu_count()))

    def _render_cap(cap):
        words = [dict(w) for w in cap["words"]]
        for w in words:
            if style_key != "elegant":
                w["word"] = w["word"].upper()
        img = _render_caption_image(words, style, max_width=max_w)
        return {
            "img": np.array(img),
            "start": cap["start"],
            "end": cap["end"],
        }

    with ThreadPoolExecutor(max_workers=cpu_threads) as ex:
        rendered = list(ex.map(_render_cap, captions))

    for item in rendered:
        clip = ImageClip(item["img"]).set_start(item["start"]).set_end(item["end"])
        if style.get("animate"):
            fd = style.get("fade_duration", 0.2)
            clip = clip.fadein(fd).fadeout(fd)
        clip = clip.set_position((pos_tuple[0] * video.w - clip.w / 2, pos_tuple[1] * video.h - clip.h / 2))
        text_clips.append(clip)

    composite = None
    try:
        composite = CompositeVideoClip([video, *text_clips])
        composite.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
            remove_temp=True,
            threads=8 if fast else 4,
            preset="ultrafast" if fast else "medium",
            bitrate="5M" if fast else None,
            fps=min(video.fps or 30, 24 if fast else 30),
            logger=None,
        )
    finally:
        if composite:
            composite.close()
        video.close()
        for clip in text_clips:
            try:
                clip.close()
            except Exception:
                pass
        gc.collect()
    duration = time.perf_counter() - started_at
    return {"output_path": Path(output_path), "burn_seconds": duration}
