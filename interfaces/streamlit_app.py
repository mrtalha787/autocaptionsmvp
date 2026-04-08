import sys
from pathlib import Path
import hashlib
import uuid
import os
import gc
import time

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app.audio import extract_audio, ensure_storage_dirs
from app.transcribe import transcribe_audio
from app.captions import tag_emphasis, group_words, detect_emphasis_words
from app.burner import render_captions
from app.metrics import snapshot
from app.auth import authenticate_user, register_user

MAX_QUEUE = 30


st.set_page_config(
    page_title="Auto Captions Generator",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    body {background-color: #0b0b0d; color: #f5f5f5;}
    .stButton>button {background: linear-gradient(90deg,#8c6bff,#f0b90b); color:black; border:none;}
    </style>
    """,
    unsafe_allow_html=True,
)

uploads_dir, outputs_dir = ensure_storage_dirs(BASE_DIR)
users_store = BASE_DIR / "storage" / "users.json"


def _init_session():
    if "queue" not in st.session_state:
        st.session_state.queue = []
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None


def _parse_emphasis(raw: str) -> list[str]:
    return [w.strip() for w in raw.split(",") if w.strip()]


def _add_to_queue(
    files,
    style: str,
    pos_x: float,
    pos_y: float,
    fast_mode: bool,
    burn_mode: str,
    emphasized_words: list[str],
    auto_emphasis: bool,
):
    if not files:
        st.warning("Upload at least one video to add it to the queue.")
        return

    added = 0
    skipped = 0
    for f in files:
        if len(st.session_state.queue) >= MAX_QUEUE:
            st.warning(f"Queue limit reached ({MAX_QUEUE}).")
            break
        data = f.getbuffer()
        file_hash = hashlib.md5(data).hexdigest()
        if any(job["file_hash"] == file_hash for job in st.session_state.queue):
            skipped += 1
            continue

        ts = int(time.time() * 1000)
        safe_name = f"{ts}_{f.name}"
        video_path = uploads_dir / safe_name
        video_path.write_bytes(data)

        st.session_state.queue.append(
            {
                "id": str(uuid.uuid4()),
                "file_hash": file_hash,
                "filename": f.name,
                "video_path": str(video_path),
                "style": style,
                "pos_x": pos_x,
                "pos_y": pos_y,
                "fast": fast_mode,
                "burn_mode": burn_mode,
                "emphasized_words": emphasized_words,
                "auto_emphasis": auto_emphasis,
                "resolved_emphasis": [],
                "status": "pending",
                "output_path": None,
                "burn_seconds": None,
                "error": None,
                "transcript": None,
                "words": None,
            }
        )
        added += 1

    if added:
        st.success(f"Added {added} video(s) to the queue.")
    if skipped:
        st.info(f"Skipped {skipped} duplicate(s) based on content hash.")


def _process_queue():
    queue = st.session_state.queue
    pending = [j for j in queue if j["status"] != "done"]
    if not pending:
        st.info("No pending videos in the queue.")
        return

    total = len(pending)
    progress = st.progress(0.0)
    completed = 0

    for job in queue:
        if job["status"] == "done":
            continue

        audio_path = None
        job["status"] = "processing"
        with st.spinner(f"Processing {job['filename']} ({completed + 1}/{total})"):
            try:
                audio_path = extract_audio(job["video_path"], uploads_dir)
                trans_result = transcribe_audio(audio_path)

                auto_words = detect_emphasis_words(trans_result["words"]) if job.get("auto_emphasis") else []
                combined_emph = list(dict.fromkeys([*job["emphasized_words"], *auto_words]))
                job["resolved_emphasis"] = combined_emph

                tagged = tag_emphasis(trans_result["words"], combined_emph)
                captions = group_words(tagged)

                output_path = outputs_dir / f"{Path(job['video_path']).stem}_{job['style']}.mp4"
                burn_result = render_captions(
                    job["video_path"],
                    captions,
                    job["style"],
                    output_path,
                    position_xy=(job["pos_x"], job["pos_y"]),
                    fast=job["fast"],
                    mode=job["burn_mode"],
                )

                job["output_path"] = str(burn_result["output_path"])
                job["burn_seconds"] = burn_result["burn_seconds"]
                job["transcript"] = trans_result["text"]
                job["words"] = trans_result["words"]
                job["status"] = "done"
                job["error"] = None
                st.caption(
                    f"Finished {job['filename']} in {burn_result['burn_seconds']:.2f}s | stats {snapshot('burn')}"
                )
            except Exception as exc:
                job["status"] = "error"
                job["error"] = str(exc)
                st.error(f"{job['filename']} failed: {exc}")
            finally:
                if audio_path and Path(audio_path).exists():
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass
                gc.collect()

        completed += 1
        progress.progress(completed / total)

    st.success("Queue processing complete.")


_init_session()

st.title("🎞️ Auto Captions Generator & Burner")

# Auth gate
if not st.session_state.logged_in:
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    with tab_login:
        uname = st.text_input("Username", key="login_user")
        pwd = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Login"):
            if authenticate_user(users_store, uname, pwd):
                st.session_state.logged_in = True
                st.session_state.username = uname
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab_signup:
        suname = st.text_input("New Username", key="signup_user")
        spwd = st.text_input("New Password", type="password", key="signup_pwd")
        if st.button("Sign Up"):
            if not suname or not spwd:
                st.error("Username and password required")
            else:
                ok = register_user(users_store, suname, spwd)
                if ok:
                    st.success("Account created. Please log in.")
                else:
                    st.error("Username already exists")
    st.stop()

st.sidebar.write(f"Logged in as: {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.queue = []
    st.rerun()

st.sidebar.write(f"Queue: {len(st.session_state.queue)}/{MAX_QUEUE}")
pending_count = len([j for j in st.session_state.queue if j["status"] != "done"])
st.sidebar.write(f"Pending: {pending_count}")

st.subheader("Build your queue (max 30 videos per session)")
uploaded_files = st.file_uploader(
    "Upload one or more videos", type=["mp4", "mov", "mkv"], accept_multiple_files=True
)

style = st.selectbox(
    "Caption Style",
    options=[
        ("hormozi", "Hormozi Style"),
        ("elegant", "Elegant Instagram"),
        ("cinematic", "Cinematic Minimal"),
    ],
    format_func=lambda x: x[1],
)[0]

pos_x = st.slider("Horizontal position (%)", 0, 100, 50, step=1)
pos_y = st.slider("Vertical position (%)", 0, 100, 85, step=1)

fast_mode = st.checkbox("Fast render (ultrafast preset, 1280px cap)", value=True)
burn_mode = st.radio("Render engine", options=["ffmpeg", "moviepy"], index=1)

auto_emphasis = st.checkbox(
    "Auto-detect emphasis words from transcript",
    value=True,
    help="If enabled, the system will pick key words (numbers, long or capitalized terms) automatically.",
)
emphasis_input = st.text_input(
    "Words to emphasize (comma-separated, optional)",
    "",
    help="Applied to every video in this queue batch.",
)

col_add, col_process, col_clear = st.columns(3)
with col_add:
    if st.button("Add to queue"):
        _add_to_queue(
            uploaded_files,
            style,
            pos_x / 100,
            pos_y / 100,
            fast_mode,
            burn_mode,
            _parse_emphasis(emphasis_input),
            auto_emphasis,
        )
with col_process:
    if st.button("Process queue (sequential)"):
        _process_queue()
with col_clear:
    if st.button("Clear queue"):
        st.session_state.queue = []
        st.info("Queue cleared.")

st.divider()
st.subheader("Queue status")

if not st.session_state.queue:
    st.info("No videos queued yet. Upload up to 30 and click Add to queue.")
else:
    for idx, job in enumerate(st.session_state.queue, start=1):
        label = f"{idx}. {job['filename']} — {job['status']}"
        expanded = job["status"] in {"error", "processing"}
        with st.expander(label, expanded=expanded):
            st.write(
                f"Style: {job['style']} | Fast: {job['fast']} | Engine: {job['burn_mode']} | "
                f"Pos: {int(job['pos_x']*100)}%, {int(job['pos_y']*100)}%"
            )
            emphasized_words = job.get("resolved_emphasis") or job.get("emphasized_words") or []
            if emphasized_words:
                mode = "auto" if job.get("auto_emphasis") else "manual"
                st.write(f"Emphasize ({mode}): {', '.join(emphasized_words)}")
            if job["status"] == "done" and job["output_path"]:
                st.write(f"Render time: {job['burn_seconds']:.2f}s")
                out_path = Path(job["output_path"])
                with open(out_path, "rb") as f:
                    st.download_button(
                        "Download processed video",
                        data=f,
                        file_name=out_path.name,
                        mime="video/mp4",
                    )
                st.video(str(out_path))
                st.text_area(
                    "Transcript",
                    job.get("transcript", ""),
                    height=160,
                    key=f"tx-{job['id']}",
                )
            elif job["status"] == "error":
                st.error(job.get("error", "Unknown error"))
