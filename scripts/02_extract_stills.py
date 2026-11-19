#!/usr/bin/env python3
"""
02_extract_stills.py
assets/video_manifest.json の selected_stills および slides/deck.yaml 内の静止画切り出し指定
（extract_from, timestamp_sec, output_fig）を読み込み、高解像度PNGを assets/figures/ に抽出する。
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "assets" / "video_manifest.json"
DECK_PATH = BASE_DIR / "slides" / "deck.yaml"
FIGURES_DIR = BASE_DIR / "assets" / "figures"


def resolve_output_path(output_fig: str) -> Path:
    """output_fig のパスを解決し、assets/figures/ 配下の出力先を返す。"""
    fig_path = Path(output_fig)
    if fig_path.is_absolute():
        return fig_path
    if fig_path.parts and fig_path.parts[0] == "assets":
        return BASE_DIR / fig_path
    return FIGURES_DIR / fig_path


def extract_still_png(video_path: Path, timestamp_sec: float, output_path: Path) -> None:
    """ffmpeg で指定秒数のフレームを高解像度PNGとして抽出する。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(timestamp_sec),
        "-i", str(video_path),
        "-frames:v", "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def collect_deck_stills(deck_data: dict) -> list[dict]:
    """slides/deck.yaml から静止画切り出し指定を収集する。"""
    tasks = []
    for slide in deck_data.get("slides", []):
        # 単一指定: still_extract: {extract_from, timestamp_sec, output_fig}
        if isinstance(slide.get("still_extract"), dict):
            tasks.append(slide["still_extract"])

        # 複数指定: stills: [{extract_from, timestamp_sec, output_fig}, ...]
        if isinstance(slide.get("stills"), list):
            for item in slide["stills"]:
                if isinstance(item, dict):
                    tasks.append(item)

        # スライド直下指定: extract_from + timestamp_sec + output_fig
        if "extract_from" in slide and "timestamp_sec" in slide and "output_fig" in slide:
            tasks.append({
                "extract_from": slide["extract_from"],
                "timestamp_sec": slide["timestamp_sec"],
                "output_fig": slide["output_fig"],
            })
    return tasks


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    if not MANIFEST_PATH.exists():
        print(f"エラー: {MANIFEST_PATH} が見つかりません。先に 01_normalize_videos.py を実行してください。")
        return 1

    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    video_map = {
        v["video_id"]: BASE_DIR / v["relative_path"]
        for v in manifest.get("videos", [])
        if "video_id" in v and "relative_path" in v
    }

    extraction_tasks: list[tuple[str, float, str]] = []

    # 1. video_manifest.json の selected_stills から収集
    for v in manifest.get("videos", []):
        vid = v.get("video_id")
        for still in v.get("selected_stills", []):
            if "timestamp_sec" in still and "output_fig" in still:
                extraction_tasks.append((vid, float(still["timestamp_sec"]), still["output_fig"]))

    # 2. slides/deck.yaml から収集
    if DECK_PATH.exists():
        with DECK_PATH.open("r", encoding="utf-8") as f:
            deck_data = yaml.safe_load(f) or {}
        for item in collect_deck_stills(deck_data):
            vid = item.get("extract_from")
            ts = item.get("timestamp_sec")
            out = item.get("output_fig")
            if vid and ts is not None and out:
                extraction_tasks.append((vid, float(ts), out))

    # 重複排除しつつ順序保持
    seen = set()
    unique_tasks = []
    for task in extraction_tasks:
        if task not in seen:
            seen.add(task)
            unique_tasks.append(task)

    if not unique_tasks:
        print("抽出対象の静止画指定がありませんでした。")
        return 0

    for vid, ts, out_fig in unique_tasks:
        if vid not in video_map:
            print(f"警告: video_id '{vid}' が video_manifest.json に存在しません。スキップします。")
            continue
        src_mp4 = video_map[vid]
        if not src_mp4.exists():
            print(f"警告: 動画ファイル {src_mp4} が見つかりません。スキップします。")
            continue

        out_path = resolve_output_path(out_fig)
        print(f"[{vid}] {ts}秒 -> {out_path.relative_to(BASE_DIR)}")
        extract_still_png(src_mp4, ts, out_path)

    print(f"完了: {len(unique_tasks)} 件の静止画抽出処理を終了しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
