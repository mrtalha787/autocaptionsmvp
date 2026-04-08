from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app.audio import extract_audio, ensure_storage_dirs
from app.transcribe import transcribe_audio
from app.captions import tag_emphasis, group_words, detect_emphasis_words
from app.burner import render_captions

app = FastAPI(title="Auto Captions Processor", version="0.2.0")

uploads_dir, outputs_dir = ensure_storage_dirs(BASE_DIR)
MAX_QUEUE = 30


def _process_video_file(
    video_path: Path,
    style: str,
    emphasized_words: List[str],
    pos_x: float,
    pos_y: float,
    fast: bool,
    auto_emphasis: bool,
):
    audio_path = None
    try:
        audio_path = extract_audio(video_path, uploads_dir)
        result = transcribe_audio(audio_path)
        detected = detect_emphasis_words(result["words"]) if auto_emphasis else []
        combined_emph = list(dict.fromkeys([*emphasized_words, *detected]))
        tagged_words = tag_emphasis(result["words"], combined_emph)
        captions = group_words(tagged_words)

        output_path = outputs_dir / f"{video_path.stem}_{style}.mp4"
        burn_result = render_captions(
            video_path,
            captions,
            style,
            output_path,
            position_xy=(pos_x, pos_y),
            fast=fast,
            mode="moviepy",
        )

        return {
            "result_path": str(burn_result["output_path"]),
            "burn_seconds": burn_result["burn_seconds"],
            "transcript": result["text"],
            "emphasis": combined_emph,
        }
    finally:
        if audio_path and Path(audio_path).exists():
            try:
                Path(audio_path).unlink()
            except Exception:
                pass


@app.post("/process")
async def process_video(
    file: UploadFile = File(...),
    style: str = Form("hormozi"),
    emphasized: str = Form(""),
    position: str = Form("bottom"),  # kept for backward compatibility
    pos_x: float = Form(0.5),
    pos_y: float = Form(0.9),
    fast: bool = Form(True),
    auto_emphasis: bool = Form(True),
):
    """
    Run full pipeline: upload -> extract audio -> transcribe -> group -> burn captions.
    `emphasized` is a comma-separated list of words.
    """
    emphasized_words = [w.strip() for w in emphasized.split(",") if w.strip()]
    video_path = uploads_dir / f"{int(time.time() * 1000)}_{file.filename}"
    with video_path.open("wb") as f:
        f.write(await file.read())

    return _process_video_file(video_path, style, emphasized_words, pos_x, pos_y, fast, auto_emphasis)


@app.post("/process-batch")
async def process_batch(
    files: List[UploadFile] = File(...),
    style: str = Form("hormozi"),
    emphasized: str = Form(""),
    pos_x: float = Form(0.5),
    pos_y: float = Form(0.9),
    fast: bool = Form(True),
    auto_emphasis: bool = Form(True),
):
    """
    Queue-aware batch processor. Sequentially handles up to 30 videos in one request.
    """
    if len(files) > MAX_QUEUE:
        raise HTTPException(status_code=400, detail=f"Limit of {MAX_QUEUE} videos per request.")

    emphasized_words = [w.strip() for w in emphasized.split(",") if w.strip()]
    results = []

    for file in files:
        video_path = uploads_dir / f"{int(time.time() * 1000)}_{file.filename}"
        with video_path.open("wb") as f:
            f.write(await file.read())

        res = _process_video_file(video_path, style, emphasized_words, pos_x, pos_y, fast, auto_emphasis)
        res["input_filename"] = file.filename
        results.append(res)

    return {"count": len(results), "results": results}
