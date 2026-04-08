"""
Generate ASS subtitle scripts for fast FFmpeg burning.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict


STYLE_TEMPLATES = {
    "hormozi": {
        "Name": "Hormozi",
        "Fontname": "Arial Black",
        "Fontsize": 58,
        "PrimaryColour": "&H00FFFF00",  # yellow
        "SecondaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H64000000",
        "Bold": -1,
        "BorderStyle": 1,
        "Outline": 3,
        "Shadow": 0,
        "Alignment": 2,  # bottom-center
        "MarginL": 20,
        "MarginR": 20,
        "MarginV": 40,
    },
    "elegant": {
        "Name": "Elegant",
        "Fontname": "Helvetica Neue",
        "Fontsize": 52,
        "PrimaryColour": "&H0037AFD4",  # gold-ish
        "SecondaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00101010",
        "BackColour": "&H00000000",
        "Bold": 0,
        "BorderStyle": 1,
        "Outline": 1.5,
        "Shadow": 1,
        "Alignment": 2,
        "MarginL": 20,
        "MarginR": 20,
        "MarginV": 50,
    },
    "cinematic": {
        "Name": "Cinematic",
        "Fontname": "Arial",
        "Fontsize": 54,
        "PrimaryColour": "&H00FFFFFF",
        "SecondaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H80202020",  # semi-transparent box
        "Bold": -1,
        "BorderStyle": 3,  # box
        "Outline": 2,
        "Shadow": 0,
        "Alignment": 2,
        "MarginL": 30,
        "MarginR": 30,
        "MarginV": 60,
    },
}


def _fmt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text: str) -> str:
    return text.replace(",", " ").replace("{", "").replace("}", "").strip()


def build_ass(captions: List[Dict], style_key: str, path: Path) -> Path:
    style = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES["hormozi"])
    lines = []
    lines.append("[Script Info]")
    lines.append("ScriptType: v4.00+")
    lines.append("WrapStyle: 2")
    lines.append("ScaledBorderAndShadow: yes")
    lines.append("PlayResX: 1280")
    lines.append("PlayResY: 720")
    lines.append("")
    lines.append("[V4+ Styles]")
    fields = [
        "Name",
        "Fontname",
        "Fontsize",
        "PrimaryColour",
        "SecondaryColour",
        "OutlineColour",
        "BackColour",
        "Bold",
        "Italic",
        "Underline",
        "StrikeOut",
        "ScaleX",
        "ScaleY",
        "Spacing",
        "Angle",
        "BorderStyle",
        "Outline",
        "Shadow",
        "Alignment",
        "MarginL",
        "MarginR",
        "MarginV",
        "Encoding",
    ]
    defaults = {
        "Italic": 0,
        "Underline": 0,
        "StrikeOut": 0,
        "ScaleX": 100,
        "ScaleY": 100,
        "Spacing": 0,
        "Angle": 0,
        "Encoding": 0,
    }
    fmt_line = ",".join(["Style"] + fields)
    lines.append(fmt_line)
    style_line = ",".join(str(style.get(f, defaults.get(f, 0))) for f in fields)
    lines.append(style_line)
    lines.append("")
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for cap in captions:
        text_parts = []
        for w in cap["words"]:
            txt = _clean(w["word"])
            if w.get("emphasized"):
                text_parts.append(r"{\b1\fs%s\c&H00FFFF00&}%s{\b0}" % (style["Fontsize"] + 6, txt))
            else:
                text_parts.append(txt)
        # wrap into lines separated by \N (already pre-wrapped in captions if needed)
        line_text = " ".join(text_parts)
        start = _fmt_time(cap["start"])
        end = _fmt_time(cap["end"])
        evt = f"Dialogue: 0,{start},{end},{style['Name']},,0,0,0,,{line_text}"
        lines.append(evt)

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
