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
    if "current_video" not in st.session_state:
        st.session_state.current_video = None
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


def _process_single_video(
    uploaded_file,
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
    """Process a single uploaded video."""
    print(f"[STREAMLIT] Processing single video - Username: {username}, File: {uploaded_file.name}", file=sys.stderr)
    if not uploaded_file:
        st.warning("Please upload a video to process.")
        return

    data = uploaded_file.getbuffer()
    file_hash = hashlib.md5(data).hexdigest()
    print(f"[STREAMLIT] File hash: {file_hash}, Size: {len(data)} bytes", file=sys.stderr)

    # Save uploaded file to uploads directory
    print(f"[STREAMLIT] Saving file to storage...", file=sys.stderr)
    with TemporaryDirectory() as td:
        temp_dir = Path(td)
        video_path = temp_dir / f"{int(time.time() * 1000)}_{uploaded_file.name}"
        video_path.write_bytes(data)

        # Copy to uploads storage
        timestamp = int(time.time() * 1000)
        safe_filename = f"{username}_{timestamp}_{uploaded_file.name}"
        upload_dest = UPLOADS_DIR / safe_filename
        upload_dest.write_bytes(data)
        print(f"[STREAMLIT] File saved to: {upload_dest}", file=sys.stderr)

        # Create job entry
        job_id = str(uuid.uuid4())
        print(f"[STREAMLIT] Creating job - Job ID: {job_id}, Emphasis: {emphasized_words}", file=sys.stderr)
        job = {
            "job_id": job_id,
            "username": username,
            "filename": uploaded_file.name,
            "file_hash": file_hash,
            "status": "processing",
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

        # Process the video immediately
        print(f"[STREAMLIT] Starting processing - Job ID: {job_id}", file=sys.stderr)
        with st.spinner(f"Processing {uploaded_file.name}... This may take a few minutes."):
            try:
                # Download/read uploaded file
                video_file = Path(job["uploaded_path"])
                print(f"[STREAMLIT] Video path: {video_file}", file=sys.stderr)
                if not video_file.exists():
                    raise FileNotFoundError(f"Video file not found: {video_file}")
                print(f"[STREAMLIT] Video file exists, size: {video_file.stat().st_size} bytes", file=sys.stderr)

                # Extract audio and transcribe
                print(f"[STREAMLIT] Starting audio extraction and transcription...", file=sys.stderr)
                audio_path = extract_audio(video_file, temp_dir)
                trans_result = transcribe_audio(audio_path)
                print(f"[STREAMLIT] Transcription complete - Text: {trans_result['text'][:100]}...", file=sys.stderr)

                # Detect emphasis
                print(f"[STREAMLIT] Detecting emphasis words - Auto-emphasis: {auto_emphasis}, Manual: {emphasized_words}", file=sys.stderr)
                auto_words = (
                    detect_emphasis_words(trans_result["words"])
                    if auto_emphasis
                    else []
                )
                combined_emph = list(
                    dict.fromkeys([*emphasized_words, *auto_words])
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
                    temp_dir / f"{Path(video_file).stem}_output.mp4"
                )
                burn_result = render_captions(
                    video_file,
                    captions,
                    output_path,
                    pos_x=pos_x,
                    pos_y=pos_y,
                    fast_mode=fast_mode,
                    font_name=font_name,
                    font_size=font_size,
                    font_color=font_color,
                    style_preset=style_preset,
                    render_method=render_method,
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

                st.success(f"✅ Video processed successfully in {burn_result['burn_seconds']:.2f}s!")
                st.session_state.current_video = job
                st.rerun()

            except Exception as exc:
                print(f"[STREAMLIT] ERROR processing video - {type(exc).__name__}: {str(exc)}", file=sys.stderr)
                job["status"] = "error"
                job["error_message"] = str(exc)
                _save_job_to_file(job)
                st.error(f"❌ Processing failed: {exc}")
            finally:
                print(f"[STREAMLIT] Cleaning up resources...", file=sys.stderr)
                gc.collect()








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

st.sidebar.write(f"📌 Logged in as: **{st.session_state.username}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

st.sidebar.divider()
st.sidebar.write("**Processing Status**")
user_jobs = _get_user_jobs(st.session_state.username)
done_count = len([j for j in user_jobs if j.get("status") == "done"])
error_count = len([j for j in user_jobs if j.get("status") == "error"])
st.sidebar.write(f"✅ Completed: {done_count} | ❌ Errors: {error_count}")

# Single video upload section
st.subheader("📹 Upload & Process Video")
st.write("Upload one video, configure captions, and process it.")

uploaded_file = st.file_uploader(
    "Choose a video file", type=["mp4", "mov", "mkv"]
)

if uploaded_file:
    st.info(f"📄 Selected: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f} MB)")

st.divider()
st.subheader("⚙️ Caption Settings")

col1, col2, col3 = st.columns(3)
with col1:
    pos_x = st.slider("Horizontal position (%)", 0, 100, 50, step=1)
with col2:
    pos_y = st.slider("Vertical position (%)", 0, 100, 50, step=1)
with col3:
    fast_mode = st.checkbox("⚡ Fast render", value=True, help="Faster processing, 1280px width limit")

auto_emphasis = st.checkbox(
    "🎯 Auto-detect emphasis words",
    value=True,
    help="Automatically emphasize numbers, long words, and capitalized terms"
)

emphasis_input = st.text_input(
    "📝 Additional words to emphasize (comma-separated, optional)",
    "",
    help="Example: important, critical, deadline"
)

st.divider()
st.subheader("✨ Caption Styling")

style_col1, style_col2, style_col3 = st.columns(3)
with style_col1:
    font_name = st.selectbox(
        "Font",
        ["Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"],
        index=0,
    )
with style_col2:
    font_size = st.slider("Font size", 0, 120, 60, step=5)
with style_col3:
    font_color = st.color_picker("Font color", "#00FFFF")

preset_col1, preset_col2 = st.columns(2)
with preset_col1:
    style_preset = st.selectbox(
        "Style preset",
        ["classic", "bold", "outlined"],
        index=0,
        help="classic: Standard | bold: Extra bold | outlined: Outline effect"
    )
with preset_col2:
    render_method = st.radio(
        "Render method",
        ["ass", "textclip"],
        index=0,
        format_func=lambda x: "ASS (Fast)" if x == "ass" else "TextClip (Quality)",
        horizontal=True,
    )

st.divider()

# Process button
if st.button("🚀 Process Video", use_container_width=True, type="primary"):
    if not uploaded_file:
        st.error("⚠️ Please upload a video first")
    else:
        _process_single_video(
            uploaded_file,
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

st.divider()
st.subheader("📚 Processing History")

if not user_jobs:
    st.info("No videos processed yet.")
else:
    for idx, job in enumerate(user_jobs, start=1):
        status_emoji = {"done": "✅", "error": "❌", "processing": "⏳"}.get(job["status"], "📋")
        label = f"{status_emoji} {job['filename']} — {job['status']}"
        expanded = job["status"] in {"error", "processing"}
        
        with st.expander(label, expanded=expanded):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Created:** {job.get('created_at', 'N/A')}")
                st.write(f"**Status:** {job['status'].upper()}")
            with col2:
                if job["status"] == "done":
                    st.write(f"**Render time:** {job.get('burn_seconds', 'N/A'):.2f}s")
                elif job["status"] == "error":
                    st.write(f"**Error:** {job.get('error_message', 'Unknown error')}")
            
            # Settings summary
            pos_x_stored = job.get('pos_x', 0.5)
            pos_y_stored = job.get('pos_y', 0.5)
            st.write(
                f"🎨 **Settings:** {job.get('font_name', 'Arial')} | "
                f"Pos: {int(pos_x_stored*100)}%, {int(pos_y_stored*100)}% | "
                f"Render: {job.get('render_method', 'ass').upper()}"
            )
            
            emphasized = job.get("resolved_emphasis") or job.get("emphasized_words") or []
            if emphasized:
                st.write(f"**Emphasized words:** {', '.join(emphasized)}")
            
            # Output section
            if job["status"] == "done" and job.get("output_path"):
                output_path = Path(job["output_path"])
                if output_path.exists():
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download video",
                            data=f.read(),
                            file_name=output_path.name,
                            mime="video/mp4",
                            use_container_width=True,
                        )
                else:
                    st.warning(f"Output file not found")
                
                if job.get("transcript"):
                    with st.expander("📄 View Transcript"):
                        st.text_area(
                            "Transcript",
                            job["transcript"],
                            height=160,
                            key=f"tx-{job['job_id']}",
                            disabled=True,
                        )
            elif job["status"] == "error":
                st.error(f"**Error Details:** {job.get('error_message', 'Unknown error')}")


