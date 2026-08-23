from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .cli import main as echoshield_main
from .media import check_ffmpeg


def _generate_demo(path: Path, duration: float) -> None:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=0x20242b:s=640x360:r=25:d={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=659.25:sample_rate=48000:duration={duration}",
        "-filter_complex", "[1:a][2:a]amix=inputs=2:weights='1 0.35',volume=0.25[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(path),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="echoshield-demo")
    parser.add_argument("--output-dir", type=Path, default=Path("demo_output"))
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--profile", choices=("mild", "codec", "resample"), default="codec")
    parser.add_argument("--padding-test", action="store_true")
    parser.add_argument("--padding-seconds", type=float, default=3.0)
    args = parser.parse_args(argv)

    check_ffmpeg()
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    input_path = out_dir / "demo_input.mp4"
    output_path = out_dir / "demo_output.mp4"
    _generate_demo(input_path, args.duration)
    print(f"Generated demo input: {input_path}")

    cli_args = [
        str(input_path), "-o", str(output_path), "--profile", args.profile,
        "--window-seconds", "4", "--step-seconds", "2",
    ]
    if args.padding_test:
        cli_args += ["--padding-test", "--padding-seconds", str(args.padding_seconds)]

    rc = echoshield_main(cli_args)
    if rc == 0:
        print(f"\nDemo completed. Open: {output_path.with_name(output_path.stem + '_report.html')}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
