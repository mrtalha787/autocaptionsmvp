import psutil
import time
from pathlib import Path

_proc = psutil.Process()


def snapshot(label: str, extra: dict | None = None) -> dict:
    """Return a metrics snapshot for debugging."""
    mem = _proc.memory_info().rss / (1024 * 1024)
    cpu = _proc.cpu_percent(interval=None)
    open_files = len(_proc.open_files())
    handles = _proc.num_handles() if hasattr(_proc, "num_handles") else None
    data = {
        "label": label,
        "mem_mb": round(mem, 2),
        "cpu_percent": cpu,
        "open_files": open_files,
        "handles": handles,
        "timestamp": time.time(),
    }
    if extra:
        data.update(extra)
    return data
