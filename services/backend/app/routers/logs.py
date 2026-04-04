import asyncio
import json
import os
import re
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.config import LOG_FILE

router = APIRouter()

_API_KEY_RE = re.compile(r"(apiKey=)[^&\s]+", re.IGNORECASE)
_LOG_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(\S+)\s+[—\-–]\s+(.*)"
)


def _parse_log_line(line: str) -> dict | None:
    m = _LOG_RE.match(line)
    if not m:
        return None
    return {
        "time":    m.group(1),
        "level":   m.group(2),
        "source":  m.group(3),
        "message": _API_KEY_RE.sub(r"\1REDACTED", m.group(4)),
    }


def _tail_log_file(path: str, limit: int) -> list[str]:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return []
    try:
        try:
            size = os.fstat(fd).st_size
        except OSError:
            return []
        if size == 0:
            return []

        chunk_size = min(size, limit * 4096)
        try:
            os.lseek(fd, max(size - chunk_size, 0), os.SEEK_SET)
            raw = os.read(fd, chunk_size)
        except OSError:
            return []

        text  = raw.decode("utf-8", errors="replace")
        lines = text.split("\n")
        if size > chunk_size:
            lines = lines[1:]
        if lines and not lines[-1]:
            lines.pop()
        return lines[-limit:]
    finally:
        os.close(fd)


@router.get("")
def get_logs(
    level: Optional[str] = Query(None),
    limit: int           = Query(100, ge=1, le=1000),
):
    raw_lines = _tail_log_file(LOG_FILE, limit * 2)
    entries: list[dict] = []
    for line in raw_lines:
        entry = _parse_log_line(line)
        if entry is None:
            continue
        if level and entry["level"] != level.upper():
            continue
        entries.append(entry)
    return entries[-limit:]


@router.get("/stream")
async def stream_logs():
    async def generator():
        fd: int | None = None
        inode: int = 0
        pos: int = 0

        def _open():
            f    = os.open(LOG_FILE, os.O_RDONLY)
            stat = os.fstat(f)
            return f, stat.st_ino, stat.st_size

        try:
            while True:
                if fd is None:
                    try:
                        fd, inode, size = _open()
                        pos = size
                    except OSError:
                        await asyncio.sleep(2)
                        continue

                try:
                    cur_stat = os.stat(LOG_FILE)
                except OSError:
                    os.close(fd); fd = None
                    await asyncio.sleep(1)
                    continue

                if cur_stat.st_ino != inode or cur_stat.st_size < pos:
                    os.close(fd)
                    try:
                        fd, inode, size = _open(); pos = 0
                    except OSError:
                        fd = None
                        await asyncio.sleep(1)
                        continue

                try:
                    os.lseek(fd, pos, os.SEEK_SET)
                    raw = os.read(fd, 65536)
                except OSError:
                    os.close(fd); fd = None
                    await asyncio.sleep(1)
                    continue

                if raw:
                    text = raw.decode("utf-8", errors="replace")
                    pos += len(raw)
                    for line in text.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        entry = _parse_log_line(line)
                        if entry:
                            yield f"data: {json.dumps(entry)}\n\n"

                await asyncio.sleep(1)
        finally:
            if fd is not None:
                os.close(fd)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
