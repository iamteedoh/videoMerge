# videoMerge

[![CI](https://github.com/iamteedoh/videoMerge/actions/workflows/ci.yml/badge.svg)](https://github.com/iamteedoh/videoMerge/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-%E2%9D%A4-ea4aaa?logo=githubsponsors)](https://github.com/sponsors/iamteedoh)
[![Patreon](https://img.shields.io/badge/Patreon-support-f96854?logo=patreon)](https://patreon.com/iamteedoh)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-ffdd00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/iamteedoh)

Merge segmented video clips back into one full-length file per folder, using
ffmpeg. Point it at a directory and it finds the video files in that directory
and in each first-level subfolder, sorts them naturally (`clip_2` before
`clip_10`), and concatenates each folder's clips into a single output file.

## Requirements

- Python 3.12 or newer (standard library only — nothing to `pip install`)
- [ffmpeg](https://ffmpeg.org/) on your `PATH`

The script detects which ffmpeg encoders are available and picks the best
match automatically (for MP4-style output: `libx264` → `libopenh264` →
`mpeg4`; for WebM: `libvpx-vp9` → `libvpx`). If your ffmpeg build has no
usable video encoder, it prints platform-specific install instructions
(Homebrew on macOS, RPM Fusion on Fedora/RHEL, `libavcodec-extra` on
Debian/Ubuntu) and exits.

## Usage

```bash
python3 merge_videos.py
```

The script is interactive:

1. **Enter the path** containing your videos (tab completion is supported
   where the `readline` module is available). Videos are collected from that
   directory and from each of its first-level subfolders.
2. **Choose whether to sanitize** — optionally re-encode every clip first to
   stabilize streams and eliminate decoder warnings. Slower, but more robust
   for clips with mismatched codecs or broken timestamps.
3. **Pick the scope** — when several folders contain videos, merge all of
   them or select a single folder.

For each folder, the merged file is written to a new `combined/` subdirectory
(or `combined_1/`, `combined_2/`, ... if one already exists) as
`<folder>_full.<ext>`, where the extension comes from the first clip in the
folder. The merge first attempts a fast lossless stream copy and falls back to
a re-encode when the clips cannot be concatenated as-is. Recognized input
extensions: `.mp4`, `.mov`, `.mkv`, `.avi`, `.flv`, `.wmv`, `.m4v`, `.webm`.

Example:

```text
Enter the full path containing your videos: /path/to/recordings
Optional: re-encode each clip before merging to eliminate decoder warnings.
Enable sanitizing re-encode? [Y/n]: y
Multiple folders with videos detected. Select an option:
  1) Merge all folders
  2) Merge a single folder
Enter 1 or 2: 1
Processing folder 1/2 ( 50.0%): /path/to/recordings/session_a
  Using encoders: video=libx264, audio=aac
Merging 12 videos in '/path/to/recordings/session_a' -> '/path/to/recordings/session_a/combined/session_a_full.mp4'
```

Original clips are never modified or deleted; temporary sanitize files are
cleaned up automatically.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, the validation
commands CI runs, and the pull request process.

## Security

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md) —
never through public issues.

## License

videoMerge is licensed under the
[GNU General Public License v3.0 or later](LICENSE).
