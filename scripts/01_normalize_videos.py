#!/usr/bin/env python3
"""
01_normalize_videos.py
raw_inputs/raw_videos/ 内の動画を会場Windows標準環境再生用MP4（H.264/yuv420p/30fps/幅1280px/音声なし）に変換し、
1秒ごとのプレビューJPGとメタデータ assets/video_manifest.json を生成する。
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_VIDEOS_DIR = BASE_DIR / "raw_inputs" / "raw_videos"
FRAME_PREVIEWS_DIR = BASE_DIR / "raw_inputs" / "frame_previews"
NORMALIZED_DIR = BASE_DIR / "assets" / "videos_normalized"
MANIFEST_PATH = BASE_DIR / "assets" / "video_manifest.json"

SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".wmv", ".mkv", ".mpg"}


def get_video_duration(video_path: Path) -> float:
    """ffprobe を用いて動画の長さ（秒）を取得する。"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    try:
        return round(float(result.stdout.strip()), 2)
    except ValueError:
        return 0.0


def normalize_video(src_path: Path, dst_path: Path) -> None:
    """動画を H.264 (yuv420p) / 30fps / 幅1280px / 音声なし MP4 に変換する。"""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(src_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-vf", "scale=1280:-2",
        "-an",
        "-movflags", "+faststart",
        str(dst_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def generate_frame_previews(src_mp4: Path, preview_dir: Path) -> None:
    """1秒ごとのサムネイルJPGを出力する。"""
    preview_dir.mkdir(parents=True, exist_ok=True)
    for old_file in preview_dir.glob("*.jpg"):
        old_file.unlink()

    output_pattern = preview_dir / "sec_%04d.jpg"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(src_mp4),
        "-vf", "fps=1,scale=640:-2",
        "-q:v", "3",
        str(output_pattern),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def load_existing_manifest() -> dict:
    """既存の video_manifest.json があれば clinical_label 等を引き継ぐため読み込む。"""
    if not MANIFEST_PATH.exists():
        return {}
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {v["original_name"]: v for v in data.get("videos", []) if "original_name" in v}
    except Exception:
        return {}


def main() -> int:
    RAW_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    FRAME_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    video_files = sorted(
        [p for p in RAW_VIDEOS_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    )

    if not video_files:
        print(f"警告: {RAW_VIDEOS_DIR} に対象の動画ファイルが見つかりません。")
        MANIFEST_PATH.write_text(json.dumps({"videos": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    existing_by_name = load_existing_manifest()
    manifest_videos = []

    for idx, src_path in enumerate(video_files, start=1):
        video_id = f"VID_{idx:02d}"
        dst_path = NORMALIZED_DIR / f"{video_id}.mp4"
        preview_dir = FRAME_PREVIEWS_DIR / video_id

        print(f"[{video_id}] 変換中: {src_path.name} -> {dst_path.relative_to(BASE_DIR)}")
        normalize_video(src_path, dst_path)

        print(f"[{video_id}] 1秒毎プレビュー生成中: {preview_dir.relative_to(BASE_DIR)}/")
        generate_frame_previews(dst_path, preview_dir)

        duration_sec = get_video_duration(dst_path)
        prev_entry = existing_by_name.get(src_path.name, {})

        manifest_videos.append({
            "video_id": video_id,
            "original_name": src_path.name,
            "relative_path": str(dst_path.relative_to(BASE_DIR)),
            "duration_sec": duration_sec,
            "clinical_label": prev_entry.get("clinical_label", ""),
            "selected_stills": prev_entry.get("selected_stills", []),
        })

    MANIFEST_PATH.write_text(
        json.dumps({"videos": manifest_videos}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"完了: {len(manifest_videos)} 本の動画を処理し、{MANIFEST_PATH.relative_to(BASE_DIR)} を出力しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
