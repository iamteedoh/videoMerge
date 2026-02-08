#!/usr/bin/env python3

"""Merge segmented videos back into full-length clips per folder."""

import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

try:
    import readline
except ImportError:  # pragma: no cover - readline not always available
    readline = None


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".flv",
    ".wmv",
    ".m4v",
    ".webm",
}


@dataclass
class EncoderConfig:
    """Holds the selected video/audio encoder and their CLI arguments."""

    video_encoder: str
    video_args: List[str] = field(default_factory=list)
    audio_encoder: str = ""
    audio_args: List[str] = field(default_factory=list)


# Preference-ordered encoder lists: (encoder_name, extra_cli_args)
_VIDEO_ENCODERS_MP4 = [
    ("libx264", ["-preset", "medium", "-crf", "18"]),
    ("libopenh264", ["-b:v", "4M"]),
    ("mpeg4", ["-q:v", "3"]),
]

_VIDEO_ENCODERS_WEBM = [
    ("libvpx-vp9", ["-b:v", "0", "-crf", "30"]),
    ("libvpx", ["-b:v", "4M"]),
]

_AUDIO_ENCODERS_MP4 = [
    ("aac", ["-b:a", "192k"]),
    ("ac3", ["-b:a", "192k"]),
]

_AUDIO_ENCODERS_WEBM = [
    ("libopus", ["-b:a", "128k"]),
    ("libvorbis", ["-b:a", "192k"]),
]


def detect_available_encoders() -> Set[str]:
    """Run ``ffmpeg -encoders`` and return the set of available encoder names."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders", "-hide_banner"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        encoders: Set[str] = set()
        for line in result.stdout.splitlines():
            # Encoder lines look like: " V..... libx264  ..."
            parts = line.strip().split()
            if len(parts) >= 2 and len(parts[0]) >= 6:
                encoders.add(parts[1])
        return encoders
    except (subprocess.SubprocessError, OSError):
        return set()


def _install_codec_hint() -> str:
    """Return platform-specific instructions for installing codec packages."""
    system = platform.system()
    if system == "Linux":
        # Detect distro family
        os_release = Path("/etc/os-release")
        distro_id = ""
        if os_release.exists():
            for line in os_release.read_text().splitlines():
                if line.startswith("ID_LIKE=") or line.startswith("ID="):
                    distro_id = line.split("=", 1)[1].strip('"').lower()
        if "fedora" in distro_id or "rhel" in distro_id or "centos" in distro_id:
            return (
                "On Fedora/RHEL, enable RPM Fusion and install full ffmpeg:\n"
                "  sudo dnf install "
                "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm\n"
                "  sudo dnf swap ffmpeg-free ffmpeg --allowerasing"
            )
        if "debian" in distro_id or "ubuntu" in distro_id:
            return (
                "On Debian/Ubuntu, install the full ffmpeg and codec libs:\n"
                "  sudo apt install ffmpeg libavcodec-extra"
            )
        return "Install a full ffmpeg build with libx264 and aac support for your distribution."
    if system == "Darwin":
        return (
            "On macOS, install ffmpeg via Homebrew:\n"
            "  brew install ffmpeg"
        )
    return "Install a full ffmpeg build with libx264 and aac support."


def select_encoders(available: Set[str], output_extension: str) -> EncoderConfig:
    """Pick the best available encoder combo for the given output container."""
    ext = output_extension.lower()
    is_webm = ext == ".webm"

    video_prefs = _VIDEO_ENCODERS_WEBM if is_webm else _VIDEO_ENCODERS_MP4
    audio_prefs = _AUDIO_ENCODERS_WEBM if is_webm else _AUDIO_ENCODERS_MP4

    video_encoder = None
    video_args: List[str] = []
    for name, args in video_prefs:
        if name in available:
            video_encoder = name
            video_args = args
            break

    if video_encoder is None:
        hint = _install_codec_hint()
        tried = ", ".join(name for name, _ in video_prefs)
        print(
            f"Error: No suitable video encoder found.\n"
            f"  Tried: {tried}\n"
            f"  {hint}",
            file=sys.stderr,
        )
        sys.exit(1)

    audio_encoder = ""
    audio_args_selected: List[str] = []
    for name, args in audio_prefs:
        if name in available:
            audio_encoder = name
            audio_args_selected = args
            break

    if not audio_encoder:
        print(
            f"Warning: No preferred audio encoder found; audio will be dropped.",
            file=sys.stderr,
        )

    config = EncoderConfig(
        video_encoder=video_encoder,
        video_args=video_args,
        audio_encoder=audio_encoder,
        audio_args=audio_args_selected,
    )
    print(
        f"  Using encoders: video={config.video_encoder}, "
        f"audio={config.audio_encoder or '(none)'}",
        flush=True,
    )
    return config


def natural_key(path: Path) -> Tuple:
    """Return a key for natural sorting of paths."""

    def convert(text: str):
        return int(text) if text.isdigit() else text.lower()

    parts = re.split(r"(\d+)", path.name)
    return tuple(convert(part) for part in parts)


def find_video_files(folder: Path) -> List[Path]:
    """Return sorted list of video files in a folder."""

    videos = [
        entry
        for entry in folder.iterdir()
        if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(videos, key=natural_key)


def collect_candidate_folders(root: Path) -> Dict[Path, List[Path]]:
    """Map folders to their video files if they contain any."""

    candidates: Dict[Path, List[Path]] = {}

    root_videos = find_video_files(root)
    if root_videos:
        candidates[root] = root_videos

    for entry in root.iterdir():
        if entry.is_dir():
            videos = find_video_files(entry)
            if videos:
                candidates[entry] = videos

    return candidates


def ensure_ffmpeg_available() -> Set[str]:
    """Check that ffmpeg is on PATH and return available encoders."""
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is required but was not found in PATH.")
        print("Please install ffmpeg (https://ffmpeg.org/) and try again.")
        sys.exit(1)
    return detect_available_encoders()


def write_ffmpeg_concat_file(video_files: Iterable[Path], directory: Path) -> Path:
    """Create a temporary concat list file for ffmpeg."""

    concat_file = Path(tempfile.mkstemp(dir=directory, suffix=".txt")[1])

    lines = []
    for video in video_files:
        escaped = str(video).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")

    concat_file.write_text("\n".join(lines), encoding="utf-8")
    return concat_file


def run_quiet_ffmpeg(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run ffmpeg with suppressed output; raise on failure."""

    return subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def summarize_ffmpeg_error(exc: subprocess.CalledProcessError) -> str:
    if exc.stderr:
        lines = [line for line in exc.stderr.strip().splitlines() if line]
        if lines:
            return lines[-1]
    return f"ffmpeg exited with status {exc.returncode}"


def run_ffmpeg_concat(list_file: Path, output_file: Path, enc: EncoderConfig) -> None:
    """Run ffmpeg concat, fallback to re-encode if necessary."""

    base_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "quiet",
        "-stats_period",
        "1",
        "-f",
        "concat",
        "-safe",
        "0",
        "-fflags",
        "+genpts",
        "-i",
        str(list_file),
    ]

    reencode_cmd = base_cmd + ["-c:v", enc.video_encoder] + enc.video_args
    if enc.audio_encoder:
        reencode_cmd += ["-c:a", enc.audio_encoder] + enc.audio_args
    else:
        reencode_cmd += ["-an"]
    reencode_cmd.append(str(output_file))

    variants = [
        {
            "description": "stream copy",
            "command": base_cmd + ["-c", "copy", str(output_file)],
        },
        {
            "description": "re-encode",
            "command": reencode_cmd,
        },
    ]

    last_error: subprocess.CalledProcessError | None = None
    for variant in variants:
        try:
            run_quiet_ffmpeg(variant["command"])
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc

    if last_error:
        summary = summarize_ffmpeg_error(last_error)
        raise RuntimeError(f"Failed to merge into {output_file.name}: {summary}") from last_error


def unique_directory(parent: Path, base_name: str) -> Path:
    """Return a unique subdirectory path within parent."""

    candidate = parent / base_name
    counter = 1
    while candidate.exists():
        candidate = parent / f"{base_name}_{counter}"
        counter += 1
    return candidate


def format_progress(index: int, total: int) -> str:
    percent = (index / total) * 100 if total else 100
    return f"[{index}/{total} {percent:5.1f}%]"


def _is_encoder_error(stderr: str) -> bool:
    """Check if ffmpeg stderr indicates a missing/unknown encoder."""
    lowered = stderr.lower()
    return "unknown encoder" in lowered or "encoder not found" in lowered


def transcode_clips(videos: List[Path], temp_dir: Path, enc: EncoderConfig) -> List[Path]:
    """Re-encode clips to stabilize streams before concatenation."""

    sanitized: List[Path] = []
    total = len(videos)
    for index, video in enumerate(videos, start=1):
        output_ext = ".webm" if enc.video_encoder in ("libvpx", "libvpx-vp9") else ".mp4"
        output_path = temp_dir / f"clip_{index:04d}{output_ext}"
        prefix = format_progress(index, total)
        print(f"  {prefix} Re-encoding {video.name} -> {output_path.name}", flush=True)

        core_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "+genpts",
            "-err_detect",
            "ignore_err",
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-c:v",
            enc.video_encoder,
        ] + enc.video_args

        audio_cmd: List[str] = []
        if enc.audio_encoder:
            audio_cmd = [
                "-map",
                "0:a:0?",
                "-c:a",
                enc.audio_encoder,
            ] + enc.audio_args + [
                "-ac",
                "2",
                "-ar",
                "48000",
            ]
        else:
            audio_cmd = ["-an"]

        trailer = [
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        try:
            run_quiet_ffmpeg(core_cmd + audio_cmd + trailer)
        except subprocess.CalledProcessError as exc:
            # If the error is about a missing encoder, fail immediately
            if exc.stderr and _is_encoder_error(exc.stderr):
                hint = _install_codec_hint()
                raise RuntimeError(
                    f"Encoder error while processing '{video.name}': "
                    f"{summarize_ffmpeg_error(exc)}\n  {hint}"
                ) from exc
            # Otherwise assume audio issues and retry without audio
            print("    Encountered audio issues, retrying without audio stream...", flush=True)
            fallback_cmd = core_cmd + ["-an"] + trailer
            try:
                run_quiet_ffmpeg(fallback_cmd)
            except subprocess.CalledProcessError as fallback_exc:
                summary = summarize_ffmpeg_error(fallback_exc)
                raise RuntimeError(
                    f"Failed to sanitize clip '{video.name}': {summary}"
                ) from fallback_exc

        sanitized.append(output_path)

    return sanitized


def merge_folder(
    folder: Path,
    videos: List[Path],
    *,
    sanitize: bool,
    available_encoders: Set[str],
    position: Tuple[int, int] | None = None,
) -> None:
    if not videos:
        print(f"Skipping {folder}: no video files found.")
        return

    if position:
        current, total = position
        percent = (current / total) * 100 if total else 100
        print(f"Processing folder {current}/{total} ({percent:5.1f}%): {folder}", flush=True)

    output_dir = unique_directory(folder, "combined")
    output_dir.mkdir(parents=True, exist_ok=False)

    extension = videos[0].suffix or ".mp4"
    output_filename = f"{folder.name or 'combined'}_full{extension}"
    output_path = output_dir / output_filename

    enc = select_encoders(available_encoders, extension)

    print(f"Merging {len(videos)} videos in '{folder}' -> '{output_path}'", flush=True)

    sanitized_dir: Path | None = None
    videos_to_merge = videos

    try:
        if sanitize:
            sanitized_dir = Path(tempfile.mkdtemp(prefix="sanitized_", dir=folder))
            print("Sanitizing clips before merge (this can take a while)...")
            videos_to_merge = transcode_clips(videos, sanitized_dir, enc)

        concat_dir = sanitized_dir or folder
        concat_file = write_ffmpeg_concat_file(videos_to_merge, concat_dir)

        try:
            if sanitize:
                print("  Combining sanitized clips...", flush=True)
            else:
                print("  Combining clips...", flush=True)
            run_ffmpeg_concat(concat_file, output_path, enc)
        finally:
            try:
                concat_file.unlink()
            except OSError:
                pass
    finally:
        if sanitized_dir is not None:
            shutil.rmtree(sanitized_dir, ignore_errors=True)

    print(f"Created {output_path}")


def prompt_all_or_single(folders: List[Path]) -> Tuple[str, Path | None]:
    print("Multiple folders with videos detected. Select an option:")
    print("  1) Merge all folders")
    print("  2) Merge a single folder")

    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice == "1":
            return "all", None
        if choice == "2":
            break
        print("Invalid choice. Please enter 1 or 2.")

    print("Select the folder number to merge:")
    for idx, folder in enumerate(folders, start=1):
        print(f"  {idx}) {folder}")

    while True:
        selection = input("Enter folder number: ").strip()
        if selection.isdigit():
            index = int(selection) - 1
            if 0 <= index < len(folders):
                return "single", folders[index]
        print("Invalid selection. Try again.")


def prompt_sanitize() -> bool:
    print(
        "Optional: re-encode each clip before merging to eliminate decoder warnings."
    )
    response = input("Enable sanitizing re-encode? [Y/n]: ").strip().lower()
    if response == "" or response in {"y", "yes"}:
        return True
    return False


def path_completer_factory():
    if readline is None:
        return lambda: None

    readline.set_completer_delims(" \t\n")

    def complete(text: str, state: int) -> str | None:
        expanded = os.path.expanduser(text or "")
        if expanded in {"", os.path.sep}:
            pattern = expanded + "*"
        else:
            pattern = expanded + "*"

        matches = []
        for match in glob.glob(pattern):
            display = os.path.normpath(match)
            if os.path.isdir(display) and not display.endswith(os.sep):
                display += os.sep
            matches.append(display)

        matches.sort()
        try:
            return matches[state]
        except IndexError:
            return None

    try:
        readline.parse_and_bind("tab: complete")
    except Exception:
        return lambda: None

    previous = getattr(readline, "get_completer", lambda: None)()
    readline.set_completer(complete)

    def restore() -> None:
        if hasattr(readline, "set_completer"):
            readline.set_completer(previous)

    return restore


def main() -> None:
    available_encoders = ensure_ffmpeg_available()

    restore_completer = path_completer_factory()
    try:
        target_path = input("Enter the full path containing your videos: ").strip()
    finally:
        restore_completer()
    if not target_path:
        print("No path provided. Exiting.")
        return

    root = Path(os.path.expanduser(target_path)).resolve()

    if not root.exists() or not root.is_dir():
        print(f"Error: '{root}' is not a valid directory.")
        return

    candidates = collect_candidate_folders(root)
    if not candidates:
        print("No video files found in the provided directory or its first-level subfolders.")
        return

    folders = sorted(candidates.keys())

    sanitize = prompt_sanitize()

    if len(folders) == 1:
        folder = folders[0]
        merge_folder(folder, candidates[folder], sanitize=sanitize, available_encoders=available_encoders, position=(1, 1))
        return

    mode, selected_folder = prompt_all_or_single(folders)

    if mode == "all":
        total = len(folders)
        for idx, folder in enumerate(folders, start=1):
            merge_folder(
                folder,
                candidates[folder],
                sanitize=sanitize,
                available_encoders=available_encoders,
                position=(idx, total),
            )
    elif selected_folder is not None:
        merge_folder(
            selected_folder,
            candidates[selected_folder],
            sanitize=sanitize,
            available_encoders=available_encoders,
            position=(1, 1),
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")

