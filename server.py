import json
import re
import subprocess
import threading
import time
from datetime import datetime
from email.utils import formatdate
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
RECORDINGS_DIR = BASE_DIR / "recordings"
SCHEDULES_PATH = BASE_DIR / "schedules.json"
CONFIG_PATH = BASE_DIR / "config.json"
RSS_PATH = BASE_DIR / "rss.xml"

DEFAULT_CONFIG = {
    "base_url": "http://localhost:8088",
    "rss_title": "shiftFM",
    "rss_description": "Time-shifted FM recordings",
    "rss_itunes_category": "News",
}

SAMPLE_SCHEDULES = {
    "schedules": []
}

active_recordings = set()
active_lock = threading.Lock()
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def load_json(path: Path, default_payload: dict) -> dict:
    if not path.exists():
        save_json(path, default_payload)
        return json.loads(json.dumps(default_payload))
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp_path.replace(path)


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    return cleaned.strip("-") or "recording"


def parse_time(value: str) -> tuple[int, int]:
    cleaned = value.strip()
    meridiem = None
    match = re.match(r"^(\d{1,2}):(\d{2})\s*([AaPp][Mm])?$", cleaned)
    if not match:
        raise ValueError("start_time must be HH:MM")
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(3)
    if meridiem:
        meridiem = meridiem.lower()
        if not (1 <= hour <= 12):
            raise ValueError("start_time must be HH:MM")
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("start_time must be HH:MM")
    return hour, minute


def generate_filename(name: str, frequency_mhz: float) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_name = sanitize_name(name)
    freq = f"{frequency_mhz:.1f}"
    return f"{safe_name}_{freq}_{stamp}.mp3"


def record_station(name: str, frequency_mhz: float, duration_sec: int, config: dict) -> str:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    filename = generate_filename(name, frequency_mhz)
    output_path = RECORDINGS_DIR / filename

    rtl_cmd = [
        "rtl_fm",
        "-f",
        f"{frequency_mhz}e6",
        "-M",
        "wbfm",
        "-s",
        "200k",
    ]
    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-ar",
        "16000",
        "-ac",
        "2",
        "-i",
        "-",
        "-t",
        str(duration_sec),
        str(output_path),
    ]

    rtl = subprocess.Popen(rtl_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=rtl.stdout, stderr=subprocess.DEVNULL)
    if rtl.stdout:
        rtl.stdout.close()
    ffmpeg.wait()
    rtl.terminate()
    try:
        rtl.wait(timeout=5)
    except subprocess.TimeoutExpired:
        rtl.kill()
    generate_rss(config)
    return filename


def generate_rss(config: dict) -> None:
    base_url = config.get("base_url", DEFAULT_CONFIG["base_url"]).rstrip("/")
    title = escape(config.get("rss_title", DEFAULT_CONFIG["rss_title"]))
    description = escape(config.get("rss_description", DEFAULT_CONFIG["rss_description"]))
    itunes_category = escape(
        config.get("rss_itunes_category", DEFAULT_CONFIG["rss_itunes_category"])
    )

    items = []
    for path in sorted(RECORDINGS_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        item_title = escape(path.stem.replace("_", " "))
        url = f"{base_url}/recordings/{path.name}"
        pub_date = formatdate(stat.st_mtime, usegmt=True)
        duration_sec = get_duration_seconds(path)
        duration_tag = ""
        if duration_sec is not None:
            duration_tag = f"        <itunes:duration>{format_duration(duration_sec)}</itunes:duration>"
        items.append(
            "\n".join(
                [
                    "      <item>",
                    f"        <title>{item_title}</title>",
                    f"        <enclosure url=\"{escape(url)}\" length=\"{stat.st_size}\" type=\"audio/mpeg\" />",
                    f"        <guid>{escape(url)}</guid>",
                    f"        <pubDate>{pub_date}</pubDate>",
                    duration_tag,
                    "      </item>",
                ]
            )
        )

    payload = "\n".join(
        [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\">",
            "  <channel>",
            f"    <title>{title}</title>",
            f"    <link>{escape(base_url)}/rss.xml</link>",
            f"    <description>{description}</description>",
            f"    <itunes:category text=\"{itunes_category}\" />",
            "\n".join(items),
            "  </channel>",
            "</rss>",
            "",
        ]
    )
    RSS_PATH.write_text(payload, encoding="utf-8")


def load_schedules() -> dict:
    return load_json(SCHEDULES_PATH, SAMPLE_SCHEDULES)


def load_config() -> dict:
    payload = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    merged = DEFAULT_CONFIG.copy()
    merged.update(payload)
    return merged


def get_duration_seconds(path: Path) -> Optional[int]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        return int(float(result.stdout.strip()))
    except ValueError:
        return None


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def schedule_due(schedule: dict, now: datetime) -> bool:
    if not schedule.get("enabled", True):
        return False
    days = schedule.get("days", [])
    today = now.strftime("%a").lower()[:3]
    if today not in [day.lower()[:3] for day in days]:
        return False
    try:
        hour, minute = parse_time(schedule["start_time"])
    except (KeyError, ValueError):
        return False
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delta = (now - scheduled).total_seconds()
    if delta < 0 or delta > 60:
        return False
    last_run = schedule.get("last_run")
    if last_run:
        try:
            last_time = datetime.fromisoformat(last_run)
            if last_time.date() == scheduled.date():
                return False
        except ValueError:
            pass
    return True


def normalize_days(days: list) -> list[int]:
    indices = []
    for day in days or []:
        day_key = str(day).lower()[:3]
        if day_key in DAYS:
            indices.append(DAYS.index(day_key))
    return sorted(set(indices))


def schedule_intervals(schedule: dict) -> list[tuple[int, int, int]]:
    try:
        hour, minute = parse_time(schedule["start_time"])
    except (KeyError, ValueError):
        return []
    duration_sec = int(schedule.get("duration_sec", 0))
    if duration_sec <= 0:
        return []
    start_sec = hour * 3600 + minute * 60
    end_sec = start_sec + duration_sec
    intervals = []
    for day_index in normalize_days(schedule.get("days", [])):
        if end_sec <= 86400:
            intervals.append((day_index, start_sec, end_sec))
        else:
            intervals.append((day_index, start_sec, 86400))
            intervals.append(((day_index + 1) % 7, 0, end_sec - 86400))
    return intervals


def schedules_overlap(candidate: dict, schedules: list, skip_id: Optional[str] = None) -> bool:
    candidate_intervals = schedule_intervals(candidate)
    if not candidate_intervals:
        return False
    for schedule in schedules:
        if skip_id and schedule.get("id") == skip_id:
            continue
        for cand_day, cand_start, cand_end in candidate_intervals:
            for day, start, end in schedule_intervals(schedule):
                if cand_day != day:
                    continue
                if max(cand_start, start) < min(cand_end, end):
                    return True
    return False


def run_recording(schedule: dict) -> None:
    config = load_config()
    name = schedule["name"]
    frequency = float(schedule["frequency_mhz"])
    duration = int(schedule["duration_sec"])
    key = f"{name}:{frequency}:{duration}"
    with active_lock:
        if key in active_recordings:
            return
        active_recordings.add(key)
    try:
        record_station(name, frequency, duration, config)
    finally:
        with active_lock:
            active_recordings.discard(key)


def scheduler_loop() -> None:
    while True:
        now = datetime.now()
        schedules_payload = load_schedules()
        schedules = schedules_payload.get("schedules", [])
        changed = False
        for schedule in schedules:
            if schedule_due(schedule, now):
                schedule["last_run"] = now.isoformat(timespec="seconds")
                changed = True
                threading.Thread(target=run_recording, args=(schedule,), daemon=True).start()
        if changed:
            save_json(SCHEDULES_PATH, schedules_payload)
        time.sleep(20)


class ShiftHandler(BaseHTTPRequestHandler):
    server_version = "shiftFM/0.1"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, payload: str, content_type: str = "text/plain", status: int = 200) -> None:
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        payload = self.rfile.read(length).decode("utf-8")
        if self.headers.get("Content-Type", "").startswith("application/json"):
            return json.loads(payload)
        return parse_qs(payload)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/rss.xml":
            payload = RSS_PATH.read_text(encoding="utf-8") if RSS_PATH.exists() else ""
            data = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return
        if parsed.path.startswith("/recordings/"):
            target = RECORDINGS_DIR / Path(parsed.path).name
            if target.exists():
                size = target.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(size))
                self.end_headers()
            else:
                self.send_error(404)
            return
        self.send_error(404)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/schedules":
            self._send_json(load_schedules())
            return
        if parsed.path == "/api/config":
            self._send_json(load_config())
            return
        if parsed.path == "/rss.xml":
            if RSS_PATH.exists():
                self._send_text(RSS_PATH.read_text(encoding="utf-8"), content_type="application/rss+xml")
            else:
                self._send_text("", content_type="application/rss+xml")
            return
        if parsed.path.startswith("/recordings/"):
            target = RECORDINGS_DIR / Path(parsed.path).name
            if target.exists():
                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404)
            return
        if parsed.path.startswith("/static/"):
            target = STATIC_DIR / Path(parsed.path).name
            if target.exists():
                mime = "text/plain"
                if target.suffix == ".css":
                    mime = "text/css"
                elif target.suffix == ".js":
                    mime = "application/javascript"
                self._send_text(target.read_text(encoding="utf-8"), content_type=mime)
            else:
                self.send_error(404)
            return
        if parsed.path in ("/", "/index.html"):
            self._send_text((STATIC_DIR / "index.html").read_text(encoding="utf-8"), content_type="text/html")
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/schedules":
            payload = self._read_body()
            schedules_payload = load_schedules()
            schedules = schedules_payload.get("schedules", [])
            schedule = {
                "id": f"sch_{int(time.time() * 1000)}",
                "name": payload.get("name", "Show"),
                "frequency_mhz": float(payload.get("frequency_mhz", 0)),
                "duration_sec": max(60, int(payload.get("duration_sec", 0))),
                "days": payload.get("days", []),
                "start_time": payload.get("start_time", "00:00"),
                "enabled": bool(payload.get("enabled", True)),
            }
            if schedules_overlap(schedule, schedules):
                self._send_json({"error": "Schedule overlaps an existing recording."}, status=409)
                return
            schedules.append(schedule)
            schedules_payload["schedules"] = schedules
            save_json(SCHEDULES_PATH, schedules_payload)
            self._send_json(schedule, status=201)
            return
        if self.path == "/api/record-now":
            payload = self._read_body()
            config = load_config()
            with active_lock:
                if active_recordings:
                    self._send_json({"error": "Recording already in progress."}, status=409)
                    return
            threading.Thread(
                target=record_station,
                args=(
                    payload.get("name", "Manual"),
                    float(payload.get("frequency_mhz", 0)),
                    max(60, int(payload.get("duration_sec", 0))),
                    config,
                ),
                daemon=True,
            ).start()
            self._send_json({"status": "started"})
            return
        self.send_error(404)

    def do_PUT(self) -> None:
        if self.path.startswith("/api/schedules/"):
            schedule_id = self.path.split("/")[-1]
            payload = self._read_body()
            schedules_payload = load_schedules()
            schedules = schedules_payload.get("schedules", [])
            updated = None
            for schedule in schedules:
                if schedule.get("id") == schedule_id:
                    candidate = schedule.copy()
                    candidate.update(payload)
                    if "duration_sec" in candidate:
                        candidate["duration_sec"] = max(60, int(candidate.get("duration_sec", 0)))
                    if schedules_overlap(candidate, schedules, skip_id=schedule_id):
                        self._send_json({"error": "Schedule overlaps an existing recording."}, status=409)
                        return
                    reset_last_run = any(
                        key in payload and payload.get(key) != schedule.get(key)
                        for key in ("start_time", "days", "frequency_mhz", "duration_sec")
                    )
                    schedule.update(payload)
                    if "duration_sec" in payload:
                        schedule["duration_sec"] = max(60, int(schedule.get("duration_sec", 0)))
                    if reset_last_run:
                        schedule.pop("last_run", None)
                    updated = schedule
                    break
            if updated is None:
                self.send_error(404)
                return
            schedules_payload["schedules"] = schedules
            save_json(SCHEDULES_PATH, schedules_payload)
            self._send_json(updated)
            return
        if self.path == "/api/config":
            payload = self._read_body()
            config = load_config()
            config.update(payload)
            save_json(CONFIG_PATH, config)
            generate_rss(config)
            self._send_json(config)
            return
        self.send_error(404)

    def do_DELETE(self) -> None:
        if self.path.startswith("/api/schedules/"):
            schedule_id = self.path.split("/")[-1]
            schedules_payload = load_schedules()
            schedules = schedules_payload.get("schedules", [])
            schedules = [schedule for schedule in schedules if schedule.get("id") != schedule_id]
            schedules_payload["schedules"] = schedules
            save_json(SCHEDULES_PATH, schedules_payload)
            self._send_json({"status": "deleted"})
            return
        self.send_error(404)


def main() -> None:
    load_config()
    load_schedules()
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not RSS_PATH.exists():
        generate_rss(load_config())
    scheduler = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler.start()
    server = ThreadingHTTPServer(("0.0.0.0", 8000), ShiftHandler)
    print("shiftFM web UI running on port 8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
