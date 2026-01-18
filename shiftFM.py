import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    return cleaned.strip("-") or "recording"


def record_station(frequency_mhz: float, duration_sec: int, name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_name = sanitize_name(name)
    freq = f"{frequency_mhz:.1f}"
    output_path = output_dir / f"{safe_name}_{freq}_{stamp}.mp3"

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
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Record and time-shift FM radio.")
    parser.add_argument("frequency_mhz", type=float, help="Frequency in MHz")
    parser.add_argument("duration_sec", type=int, help="Recording duration in seconds")
    parser.add_argument("name", help="Program name")
    args = parser.parse_args()

    output_dir = Path(__file__).resolve().parent / "recordings"
    output_path = record_station(args.frequency_mhz, args.duration_sec, args.name, output_dir)
    print(f"Saved recording to {output_path}")


if __name__ == "__main__":
    main()
