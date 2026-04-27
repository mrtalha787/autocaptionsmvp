import sys
import os
from pathlib import Path
import hashlib
import gc
import time
import uuid
import json
from tempfile import TemporaryDirectory

import streamlit as st

print(f"[STREAMLIT] Initializing Streamlit app...", file=sys.stderr)

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
print(f"[STREAMLIT] Base directory: {BASE_DIR}", file=sys.stderr)

from app.transcribe import transcribe_audio
from app.captions import tag_emphasis, group_words, detect_emphasis_words
from app.burner import render_captions
from app.auth import authenticate_user, register_user, load_users, save_users
from app.audio import extract_audio, ensure_storage_dirs

MAX_QUEUE = 30
STORAGE_DIR = BASE_DIR / "storage"
USERS_FILE = STORAGE_DIR / "users.json"

print(f"[STREAMLIT] Storage directory: {STORAGE_DIR}", file=sys.stderr)

# Initialize storage
UPLOADS_DIR, OUTPUTS_DIR = ensure_storage_dirs(BASE_DIR)
print(f"[STREAMLIT] Streamlit app initialized successfully", file=sys.stderr)

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




def _init_session():
    """Initialize session state."""
    print(f"[STREAMLIT] Initializing session state...", file=sys.stderr)
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
    if "queue" not in st.session_state:
        st.session_state.queue = []
    if "processed_hashes" not in st.session_state:
        st.session_state.processed_hashes = set()
    print(f"[STREAMLIT] Session state initialized - Logged in: {st.session_state.logged_in}, Username: {st.session_state.username}", file=sys.stderr)


def _parse_emphasis(raw: str) -> list[str]:
    """Parse comma-separated emphasis words."""
    return [w.strip() for w in raw.split(",") if w.strip()]


def _save_job_to_file(job_dict: dict) -> None:
    """Save job metadata to file for persistence."""
    print(f"[STREAMLIT] Saving job to file - Job ID: {job_dict['job_id']}, Status: {job_dict.get('status')}", file=sys.stderr)
    jobs_dir = STORAGE_DIR / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_file = jobs_dir / f"{job_dict['job_id']}.json"
    job_file.write_text(json.dumps(job_dict, indent=2))
    print(f"[STREAMLIT] Job saved successfully", file=sys.stderr)


def _load_job_from_file(job_id: str) -> dict | None:
    """Load job metadata from file."""
    print(f"[STREAMLIT] Loading job from file - Job ID: {job_id}", file=sys.stderr)
    job_file = STORAGE_DIR / "jobs" / f"{job_id}.json"
    if job_file.exists():
        job = json.loads(job_file.read_text())
        print(f"[STREAMLIT] Job loaded successfully - Status: {job.get('status')}", file=sys.stderr)
        return job
    print(f"[STREAMLIT] Job file not found", file=sys.stderr)
    return None


def _get_user_jobs(username: str) -> list[dict]:
    """Load all jobs for a user."""
    jobs_dir = STORAGE_DIR / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for job_file in jobs_dir.glob("*.json"):
        job = json.loads(job_file.read_text())
        if job.get("username") == username:
            jobs.append(job)
    return sorted(jobs, key=lambda x: x.get("created_at", 0), reverse=True)


def _add_to_queue(
    files,
    username: str,
    pos_x: float,
    pos_y: float,
    fast_mode: bool,
    emphasized_words: list[str],
    auto_emphasis: bool,
    font_name: str,
    font_size: int,
    font_color: str,
    style_preset: str,
    render_method: str,
):
    """Add uploaded videos to processing queue."""
    print(f"[STREAMLIT] Adding files to queue - Username: {username}, Files: {len(files) if files else 0}", file=sys.stderr)
    if not files:
        print(f"[STREAMLIT] No files provided", file=sys.stderr)
        st.warning("Upload at least one video to add it to the queue.")
        return

    added = 0
    skipped = 0

    for f_idx, f in enumerate(files, 1):
        print(f"[STREAMLIT] Processing file {f_idx}/{len(files)}: {f.name}", file=sys.stderr)
        # Check queue limit
        user_jobs = _get_user_jobs(username)
        active = [j for j in user_jobs if j.get("status") != "done"]
        if len(active) >= MAX_QUEUE:
            print(f"[STREAMLIT] Queue limit reached for user {username} - Active jobs: {len(active)}", file=sys.stderr)
            st.warning(f"Queue limit reached ({MAX_QUEUE}).")
            break

        data = f.getbuffer()
        file_hash = hashlib.md5(data).hexdigest()
        print(f"[STREAMLIT] File hash: {file_hash}, Size: {len(data)} bytes", file=sys.stderr)

        # Check for duplicates
        if any(j.get("file_hash") == file_hash and j.get("username") == username 
               for j in user_jobs if j.get("status") != "done"):
            print(f"[STREAMLIT] File already in queue (duplicate), skipping", file=sys.stderr)
            skipped += 1
            continue

        # Save uploaded file to uploads directory
        print(f"[STREAMLIT] Saving file to storage...", file=sys.stderr)
        with TemporaryDirectory() as td:
            temp_dir = Path(td)
            video_path = temp_dir / f"{int(time.time() * 1000)}_{f.name}"
            video_path.write_bytes(data)

            # Copy to uploads storage
            timestamp = int(time.time() * 1000)
            safe_filename = f"{username}_{timestamp}_{f.name}"
            upload_dest = UPLOADS_DIR / safe_filename
            upload_dest.write_bytes(data)
            print(f"[STREAMLIT] File saved to: {upload_dest}", file=sys.stderr)

        # Create job entry
        job_id = str(uuid.uuid4())
        print(f"[STREAMLIT] Creating job - Job ID: {job_id}, Emphasis: {emphasized_words}", file=sys.stderr)
        job = {
            "job_id": job_id,
            "username": username,
            "filename": f.name,
            "file_hash": file_hash,
            "status": "pending",
            "uploaded_path": str(upload_dest),
            "output_path": None,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "fast_mode": fast_mode,
            "emphasized_words": emphasized_words,
            "auto_emphasis": auto_emphasis,
            "resolved_emphasis": [],
            "transcript": None,
            "burn_seconds": None,
            "error_message": None,
            "font_name": font_name,
            "font_size": font_size,
            "font_color": font_color,
            "style_preset": style_preset,
            "render_method": render_method,
            "created_at": time.time(),
        }
        _save_job_to_file(job)
        st.session_state.queue.append(job)
        added += 1
        print(f"[STREAMLIT] Job created and queued successfully", file=sys.stderr)

    print(f"[STREAMLIT] Queue operation complete - Added: {added}, Skipped: {skipped}", file=sys.stderr)
    if added:
        st.success(f"Added {added} video(s) to the queue.")
    if skipped:
        st.info(f"Skipped {skipped} duplicate(s) based on content hash.")


def _process_queue(username: str):
    """Process all pending jobs for the user."""
    user_jobs = _get_user_jobs(username)
    pending_jobs = [j for j in user_jobs if j.get("status") == "pending"]

    if not pending_jobs:
        st.info("No pending videos in the queue.")
        return

    total = len(pending_jobs)
    progress = st.progress(0.0)
    completed = 0
    print(f"[STREAMLIT] Processing queue - Total pending jobs: {total}", file=sys.stderr)

    for job_idx, job in enumerate(pending_jobs, 1):
        print(f"[STREAMLIT] Processing job {job_idx}/{total} - Job ID: {job['job_id']}, File: {job['filename']}", file=sys.stderr)
        with st.spinner(f"Processing {job['filename']} ({completed + 1}/{total})"):
            try:
                # Download/read uploaded file
                video_path = Path(job["uploaded_path"])
                print(f"[STREAMLIT] Video path: {video_path}", file=sys.stderr)
                if not video_path.exists():
                    raise FileNotFoundError(f"Video file not found: {video_path}")
                print(f"[STREAMLIT] Video file exists, size: {video_path.stat().st_size} bytes", file=sys.stderr)

                # Extract audio and transcribe
                print(f"[STREAMLIT] Starting audio extraction and transcription...", file=sys.stderr)
                with TemporaryDirectory() as td:
                    temp_dir = Path(td)
                    audio_path = extract_audio(video_path, temp_dir)
                    trans_result = transcribe_audio(audio_path)
                    print(f"[STREAMLIT] Transcription complete - Text: {trans_result['text'][:100]}...", file=sys.stderr)

                    # Detect emphasis
                    print(f"[STREAMLIT] Detecting emphasis words - Auto-emphasis: {job['auto_emphasis']}, Manual: {job['emphasized_words']}", file=sys.stderr)
                    auto_words = (
                        detect_emphasis_words(trans_result["words"])
                        if job["auto_emphasis"]
                        else []
                    )
                    combined_emph = list(
                        dict.fromkeys([*job["emphasized_words"], *auto_words])
                    )
                    print(f"[STREAMLIT] Combined emphasis words: {combined_emph}", file=sys.stderr)

                    # Tag and group
                    print(f"[STREAMLIT] Tagging emphasis and grouping words...", file=sys.stderr)
                    tagged = tag_emphasis(trans_result["words"], combined_emph)
                    captions = group_words(tagged)
                    print(f"[STREAMLIT] Captions grouped - Total captions: {len(captions)}", file=sys.stderr)

                    # Render captions
                    print(f"[STREAMLIT] Rendering captions to video...", file=sys.stderr)
                    output_path = (
                        temp_dir / f"{Path(video_path).stem}_output.mp4"
                    )
                    # Handle both old and new job formats for position
                    pos_x = job.get('pos_x') or job.get('position_x', 0.5)
                    pos_y = job.get('pos_y') or job.get('position_y', 0.85)
                    burn_result = render_captions(
                        video_path,
                        captions,
                        output_path,
                        pos_x=pos_x,
                        pos_y=pos_y,
                        fast_mode=job["fast_mode"],
                        font_name=job.get("font_name", "Arial"),
                        font_size=job.get("font_size", 120),
                        font_color=job.get("font_color", "#00FFFF"),
                        style_preset=job.get("style_preset", "classic"),
                        render_method=job.get("render_method", "ass"),
                    )

                    # Copy output to outputs storage
                    print(f"[STREAMLIT] Copying output video to storage...", file=sys.stderr)
                    final_output = (
                        OUTPUTS_DIR / f"{job['job_id']}_output.mp4"
                    )
                    final_output.write_bytes(output_path.read_bytes())
                    print(f"[STREAMLIT] Output saved - File: {final_output}, Size: {final_output.stat().st_size} bytes", file=sys.stderr)

                # Update job status
                print(f"[STREAMLIT] Updating job status to 'done'...", file=sys.stderr)
                job["status"] = "done"
                job["output_path"] = str(final_output)
                job["transcript"] = trans_result["text"]
                job["burn_seconds"] = burn_result["burn_seconds"]
                job["resolved_emphasis"] = combined_emph
                _save_job_to_file(job)
                print(f"[STREAMLIT] Job completed successfully - Time: {burn_result['burn_seconds']:.2f}s", file=sys.stderr)

                st.caption(f"Finished {job['filename']} in {burn_result['burn_seconds']:.2f}s")

            except Exception as exc:
                print(f"[STREAMLIT] ERROR processing job - {type(exc).__name__}: {str(exc)}", file=sys.stderr)
                job["status"] = "error"
                job["error_message"] = str(exc)
                _save_job_to_file(job)
                st.error(f"{job['filename']} failed: {exc}")
            finally:
                print(f"[STREAMLIT] Cleaning up resources...", file=sys.stderr)
                gc.collect()

        completed += 1
        progress.progress(completed / total)

    print(f"[STREAMLIT] Queue processing complete - Total completed: {completed}/{total}", file=sys.stderr)
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
            if authenticate_user(USERS_FILE, uname, pwd):
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
                ok = register_user(USERS_FILE, suname, spwd)
                if ok:
                    st.success("Account created. Please log in.")
                else:
                    st.error("Username already exists")
    st.stop()

st.sidebar.write(f"Logged in as: {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

# Load user's queue from disk
user_jobs = _get_user_jobs(st.session_state.username)
pending_count = len([j for j in user_jobs if j.get("status") == "pending"])
st.sidebar.write(f"Total jobs: {len(user_jobs)}")
st.sidebar.write(f"Pending: {pending_count}")
st.sidebar.write(f"Queue limit: {MAX_QUEUE}")

st.subheader("Build your queue (max 30 videos per session)")
uploaded_files = st.file_uploader(
    "Upload one or more videos", type=["mp4", "mov", "mkv"], accept_multiple_files=True
)

pos_x = st.slider("Horizontal position (%)", 0, 100, 50, step=1)
pos_y = st.slider("Vertical position (%)", 0, 100, 85, step=1)

fast_mode = st.checkbox("Fast render (ultrafast preset, 1280px cap)", value=True)

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

# Caption customization section
st.divider()
st.subheader("✨ Caption customization")

cust_col1, cust_col2, cust_col3 = st.columns(3)
with cust_col1:
    font_name = st.selectbox(
        "Font",
        ["Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"],
        index=0,
        help="Select caption font family"
    )
with cust_col2:
    font_size = st.slider("Font size", 60, 200, 120, step=5, help="Caption size in pixels")
with cust_col3:
    font_color = st.color_picker("Font color", "#00FFFF", help="Select caption color")

style_col1, style_col2 = st.columns(2)
with style_col1:
    style_preset = st.selectbox(
        "Style preset",
        ["classic", "bold", "outlined"],
        index=0,
        help="Classic: Standard | Bold: Extra bold | Outlined: Outline effect"
    )
with style_col2:
    st.caption("🎨 Presets: Classic (clean) | Bold (thick) | Outlined (outline effect)")

render_col1, render_col2 = st.columns(2)
with render_col1:
    render_method = st.radio(
        "📹 Render method",
        ["ass", "textclip"],
        index=0,
        format_func=lambda x: "ASS Subtitles (Fast)" if x == "ass" else "Text Clips (High Quality)",
        horizontal=True,
        help="ASS: Lightweight subtitles, fast rendering | TextClip: Rendered graphics, slower but cleaner"
    )
with render_col2:
    if render_method == "ass":
        st.caption("⚡ Fast | 🎬 Embedded subtitles")
    else:
        st.caption("🎨 High quality | ⏱️ Slower")

st.divider()

col_add, col_process, col_clear = st.columns(3)
with col_add:
    if st.button("Add to queue"):
        _add_to_queue(
            uploaded_files,
            st.session_state.username,
            pos_x / 100,
            pos_y / 100,
            fast_mode,
            _parse_emphasis(emphasis_input),
            auto_emphasis,
            font_name,
            font_size,
            font_color,
            style_preset,
            render_method,
        )
with col_process:
    if st.button("Process queue (sequential)"):
        _process_queue(st.session_state.username)
with col_clear:
    if st.button("Clear queue"):
        # Delete all user's jobs
        user_jobs = _get_user_jobs(st.session_state.username)
        for job in user_jobs:
            job_file = STORAGE_DIR / "jobs" / f"{job['job_id']}.json"
            if job_file.exists():
                job_file.unlink()
        st.info("Queue cleared.")
        st.rerun()

st.divider()
st.subheader("Queue status")

# Refresh queue from disk
user_jobs = _get_user_jobs(st.session_state.username)

if not user_jobs:
    st.info("No videos queued yet. Upload up to 30 and click Add to queue.")
else:
    for idx, job in enumerate(user_jobs, start=1):
        label = f"{idx}. {job['filename']} — {job['status']}"
        expanded = job["status"] in {"error", "processing"}
        with st.expander(label, expanded=expanded):
            # Handle both old and new job formats
            pos_x = job.get('pos_x') or job.get('position_x', 0.5)
            pos_y = job.get('pos_y') or job.get('position_y', 0.85)
            st.write(
                f"Fast: {job.get('fast_mode', True)} | "
                f"Pos: {int(pos_x*100)}%, {int(pos_y*100)}% | "
                f"Render: {job.get('render_method', 'ass').upper()}"
            )
            
            # Show caption styling
            font_name = job.get("font_name", "Arial")
            font_size = job.get("font_size", 120)
            font_color = job.get("font_color", "#00FFFF")
            style_preset = job.get("style_preset", "classic")
            st.write(f"Font: {font_name} | Size: {font_size}px | Color: {font_color} | Style: {style_preset}")
            
            emphasized_words = job.get("resolved_emphasis") or job.get("emphasized_words") or []
            if emphasized_words:
                mode = "auto" if job.get("auto_emphasis") else "manual"
                st.write(f"Emphasize ({mode}): {', '.join(emphasized_words)}")
            if job["status"] == "done" and job.get("output_path"):
                st.write(f"Render time: {job['burn_seconds']:.2f}s")

                output_path = Path(job["output_path"])
                if output_path.exists():
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download video",
                            data=f.read(),
                            file_name=output_path.name,
                            mime="video/mp4",
                        )
                else:
                    st.warning(f"Output file not found: {output_path}")

                if job.get("transcript"):
                    st.text_area(
                        "Transcript",
                        job["transcript"],
                        height=160,
                        key=f"tx-{job['job_id']}",
                    )
            elif job["status"] == "error":
                st.error(job.get("error_message") or "Unknown error")


