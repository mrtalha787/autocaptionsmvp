"""
File validation utilities for detecting corrupted or invalid video files.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


# Common video file signatures (magic bytes)
VIDEO_SIGNATURES = {
    b'\x00\x00\x00\x20ftyp': "MP4",  # MP4
    b'\x00\x00\x00\x18ftyp': "MP4",  # MP4 variant
    b'\x1a\x45\xdf\xa3': "Matroska",  # MKV/WebM
    b'\x52\x49\x46\x46': "AVI/WAV",  # RIFF (AVI, WAV)
    b'\xff\xfb': "MP3",  # MP3
    b'\xff\xfa': "MP3",  # MP3 variant
}

# Minimum file size (1 MB) - videos smaller than this are likely corrupted
MIN_FILE_SIZE = 1 * 1024 * 1024

# Maximum file size (5 GB) - reasonable limit for processing
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024

# Allowed video file extensions
ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.flv', '.wmv'}


class FileValidationError(Exception):
    """Raised when a file fails validation."""
    pass


def is_valid_video_signature(file_path: str | Path) -> bool:
    """Check if file has a valid video file signature (magic bytes)."""
    file_path = Path(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)  # Read first 16 bytes
            
        if not header:
            return False
        
        # Check against known video signatures
        for signature, _ in VIDEO_SIGNATURES.items():
            if header.startswith(signature):
                return True
        
        return False
    except (IOError, OSError) as e:
        print(f"[VALIDATOR] Error reading file signature: {e}", file=sys.stderr)
        return False


def validate_file_size(file_path: str | Path) -> None:
    """Validate file size is within acceptable limits."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileValidationError(f"File does not exist: {file_path}")
    
    file_size = file_path.stat().st_size
    
    if file_size < MIN_FILE_SIZE:
        raise FileValidationError(
            f"File is too small ({file_size / 1024 / 1024:.2f} MB). "
            f"Minimum size is {MIN_FILE_SIZE / 1024 / 1024:.1f} MB. "
            f"File may be corrupted or incomplete."
        )
    
    if file_size > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File is too large ({file_size / 1024 / 1024 / 1024:.2f} GB). "
            f"Maximum size is {MAX_FILE_SIZE / 1024 / 1024 / 1024:.1f} GB."
        )


def validate_file_extension(file_path: str | Path) -> None:
    """Validate file has an allowed video extension."""
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    if extension not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Invalid file extension: {extension}. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def validate_with_ffmpeg(file_path: str | Path) -> None:
    """Use ffmpeg to validate the video file can be read."""
    file_path = Path(file_path)
    
    # Use ffmpeg to check if file is readable
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-i", str(file_path),
        "-f", "null",
        "-",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            raise FileValidationError(
                f"Video file is corrupted or unreadable: {stderr[:200]}"
            )
        
        print(f"[VALIDATOR] FFmpeg validation passed for {file_path.name}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        raise FileValidationError("File validation timed out. File may be corrupted.")
    except FileNotFoundError:
        print(f"[VALIDATOR] Warning: FFmpeg not found, skipping deep validation", file=sys.stderr)


def validate_extracted_audio(audio_path: str | Path, min_duration: float = 1.0) -> None:
    """Validate the extracted audio file is valid and has reasonable duration."""
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        raise FileValidationError(f"Extracted audio file not found: {audio_path}")
    
    file_size = audio_path.stat().st_size
    if file_size < 44 + 100:  # WAV header + minimal data
        raise FileValidationError(
            f"Extracted audio is corrupted (size: {file_size} bytes). "
            "Audio extraction may have failed."
        )
    
    # Get audio duration using ffprobe
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
            str(audio_path),
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        
        if result.returncode == 0:
            try:
                duration = float(result.stdout.decode().strip())
                if duration < min_duration:
                    raise FileValidationError(
                        f"Extracted audio is too short ({duration:.2f}s). "
                        f"Minimum duration is {min_duration}s. "
                        "Audio extraction may have failed."
                    )
                print(f"[VALIDATOR] Audio validation passed - Duration: {duration:.2f}s", file=sys.stderr)
            except ValueError:
                print(f"[VALIDATOR] Could not parse audio duration", file=sys.stderr)
    except FileNotFoundError:
        print(f"[VALIDATOR] Warning: ffprobe not found, skipping duration check", file=sys.stderr)
    except subprocess.TimeoutExpired:
        raise FileValidationError("Audio validation timed out.")


def validate_uploaded_file(file_path: str | Path) -> None:
    """
    Comprehensive validation of uploaded video file.
    Raises FileValidationError if any check fails.
    """
    file_path = Path(file_path)
    
    print(f"[VALIDATOR] Starting file validation: {file_path.name}", file=sys.stderr)
    
    # Check 1: File extension
    try:
        validate_file_extension(file_path)
        print(f"[VALIDATOR] ✓ File extension valid", file=sys.stderr)
    except FileValidationError as e:
        print(f"[VALIDATOR] ✗ Extension check failed: {e}", file=sys.stderr)
        raise
    
    # Check 2: File size
    try:
        validate_file_size(file_path)
        print(f"[VALIDATOR] ✓ File size valid", file=sys.stderr)
    except FileValidationError as e:
        print(f"[VALIDATOR] ✗ Size check failed: {e}", file=sys.stderr)
        raise
    
    # Check 3: File signature
    if not is_valid_video_signature(file_path):
        print(f"[VALIDATOR] ⚠ Unknown file signature (may still be valid)", file=sys.stderr)
    else:
        print(f"[VALIDATOR] ✓ File signature valid", file=sys.stderr)
    
    # Check 4: FFmpeg readability
    try:
        validate_with_ffmpeg(file_path)
        print(f"[VALIDATOR] ✓ FFmpeg validation passed", file=sys.stderr)
    except FileValidationError as e:
        print(f"[VALIDATOR] ✗ FFmpeg validation failed: {e}", file=sys.stderr)
        raise
    
    print(f"[VALIDATOR] ✓ File validation successful!", file=sys.stderr)
