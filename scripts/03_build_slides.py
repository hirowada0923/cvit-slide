#!/usr/bin/env python3
"""
03_build_slides.py
project.yaml と slides/deck.yaml から 16:9 (13.333 x 7.5 inches) の
dist/CVIT_Presentation_USB/presentation.pptx を生成し、使用したMP4ファイルを同梱する。
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches, Pt

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_YAML = BASE_DIR / "project.yaml"
DECK_YAML = BASE_DIR / "slides" / "deck.yaml"
MANIFEST_PATH = BASE_DIR / "assets" / "video_manifest.json"
DIST_DIR = BASE_DIR / "dist" / "CVIT_Presentation_USB"
OUTPUT_PPTX = DIST_DIR / "presentation.pptx"

FONT_NAME = "游ゴシック"

# カラーパレット（学会プレゼン向け・高コントラスト）
COLOR_NAVY = RGBColor(0x0F, 0x2C, 0x59)
COLOR_ACCENT = RGBColor(0x1D, 0x5B, 0x79)
COLOR_DARK_TEXT = RGBColor(0x1E, 0x29, 0x3B)
COLOR_MUTED = RGBColor(0x64, 0x74, 0x8B)
COLOR_LIGHT_BG = RGBColor(0xF8, 0xFA, 0xFC)
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_BORDER = RGBColor(0xCB, 0xD5, 0xE1)

# 基準スライドサイズ（13.333 x 7.5 in）に対するテンプレートスケール係数
BASE_W_IN = 13.333
BASE_H_IN = 7.5
SCALE_X = 1.0
SCALE_Y = 1.0
DRAW_HEADER_BAR = True


def sx(val_in: float) -> int:
    return int(Inches(val_in * SCALE_X))


def sy(val_in: float) -> int:
    return int(Inches(val_in * SCALE_Y))


def sf(size_pt: float) -> int:
    return max(8, int(round(size_pt * min(SCALE_X, SCALE_Y))))


def set_run_font(run, size_pt: int, bold: bool = False, color: RGBColor = COLOR_DARK_TEXT) -> None:
    run.font.name = FONT_NAME
    run.font.size = Pt(sf(size_pt))
    run.font.bold = bold
    run.font.color.rgb = color


def clear_existing_slides(prs: Presentation) -> None:
    """テンプレート内の既存スライドをリレーションごと綺麗に削除する。"""
    for sld_id in list(prs.slides._sldIdLst):
        r_id = sld_id.rId
        prs.part.drop_rel(r_id)
        prs.slides._sldIdLst.remove(sld_id)


def select_blank_layout(prs: Presentation, layout_index: int | None = None):
    """テンプレートから白紙（または最小プレースホルダー）レイアウトを選択する。"""
    if layout_index is not None and 0 <= layout_index < len(prs.slide_layouts):
        return prs.slide_layouts[layout_index]
    for lay in prs.slide_layouts:
        if lay.name.strip().lower() in {"blank", "白紙"}:
            return lay
    return min(prs.slide_layouts, key=lambda l: len(l.placeholders))


def remove_empty_placeholders(slide) -> None:
    """レイアウト由来の空プレースホルダーを削除する。"""
    for ph in list(slide.placeholders):
        sp = ph._element
        sp.getparent().remove(sp)


def add_header_bar(slide, title_text: str, subtitle_text: str = "") -> None:
    """共通のヘッダーバーとタイトルを追加する。"""
    if DRAW_HEADER_BAR:
        header = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, sx(0), sy(0), sx(13.333), sy(1.05)
        )
        header.fill.solid()
        header.fill.fore_color.rgb = COLOR_NAVY
        header.line.fill.background()
        title_color = COLOR_WHITE
        sub_color = RGBColor(0xCB, 0xD5, 0xE1)
    else:
        title_color = COLOR_NAVY
        sub_color = COLOR_MUTED

    tb = slide.shapes.add_textbox(sx(0.55), sy(0.15), sx(12.2), sy(0.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title_text
    set_run_font(run, 26, bold=True, color=title_color)

    if subtitle_text:
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = subtitle_text
        set_run_font(r2, 13, bold=False, color=sub_color)


def add_footer(slide, page_num: int, total_pages: int) -> None:
    """右下にスライド番号を追加する。"""
    tb = slide.shapes.add_textbox(sx(12.0), sy(7.05), sx(1.0), sy(0.35))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = f"{page_num} / {total_pages}"
    set_run_font(run, 11, color=COLOR_MUTED)


def create_poster_image(video_path: Path, tmp_dir: Path) -> Path:
    """動画の最初のフレームからポスター画像（PNG）を生成する。"""
    poster_path = tmp_dir / f"{video_path.stem}_poster.png"
    if not poster_path.exists():
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-frames:v", "1",
            str(poster_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return poster_path


def enable_video_autoplay_loop(slide, shape_ids: list[int]) -> None:
    """既存の p:timing を置換し、単一の p:timing で動画の自動再生・無限ループ・ミュートを設定する。"""
    if not shape_ids:
        return

    # python-pptx の add_movie() が自動生成した既存の <p:timing> を削除して重複を防ぐ
    p_ns = "http://schemas.openxmlformats.org/presentationml/2006/main"
    for existing in slide._element.findall(f"{{{p_ns}}}timing"):
        slide._element.remove(existing)

    video_nodes = []
    cmd_nodes = []
    bld_nodes = []
    next_id = 10

    for spid in shape_ids:
        v_ctn_id = next_id
        par_ctn_id = next_id + 1
        cmd_ctn_id = next_id + 2
        next_id += 3

        video_nodes.append(
            f"""
            <p:video>
              <p:cMediaNode mute="1">
                <p:cTn id="{v_ctn_id}" fill="hold" repeatCount="indefinite" display="0">
                  <p:stCondLst>
                    <p:cond delay="indefinite"/>
                  </p:stCondLst>
                </p:cTn>
                <p:tgtEl>
                  <p:spTgt spid="{spid}"/>
                </p:tgtEl>
              </p:cMediaNode>
            </p:video>
            """
        )
        cmd_nodes.append(
            f"""
            <p:par>
              <p:cTn id="{par_ctn_id}" fill="hold">
                <p:stCondLst>
                  <p:cond delay="0"/>
                </p:stCondLst>
                <p:childTnLst>
                  <p:par>
                    <p:cTn id="{par_ctn_id + 100}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="withEffect">
                      <p:stCondLst>
                        <p:cond delay="0"/>
                      </p:stCondLst>
                      <p:childTnLst>
                        <p:cmd type="call" cmd="playFrom(0.0)">
                          <p:cBhvr>
                            <p:cTn id="{cmd_ctn_id}" dur="indefinite" repeatCount="indefinite" fill="hold"/>
                            <p:tgtEl>
                              <p:spTgt spid="{spid}"/>
                            </p:tgtEl>
                          </p:cBhvr>
                        </p:cmd>
                      </p:childTnLst>
                    </p:cTn>
                  </p:par>
                </p:childTnLst>
              </p:cTn>
            </p:par>
            """
        )
        bld_nodes.append(f'<p:bldP spid="{spid}" grpId="0"/>')

    timing_xml = f"""
    <p:timing {nsdecls("p")}>
      <p:tnLst>
        <p:par>
          <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
            <p:childTnLst>
              <p:seq concurrent="1" nextAc="seek">
                <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="3" fill="hold">
                        <p:stCondLst>
                          <p:cond delay="0"/>
                        </p:stCondLst>
                        <p:childTnLst>
                          {''.join(cmd_nodes)}
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
                <p:prevCondLst>
                  <p:cond evt="onPrev" delay="0">
                    <p:tgtEl>
                      <p:sldTgt/>
                    </p:tgtEl>
                  </p:cond>
                </p:prevCondLst>
                <p:nextCondLst>
                  <p:cond evt="onNext" delay="0">
                    <p:tgtEl>
                      <p:sldTgt/>
                    </p:tgtEl>
                  </p:cond>
                </p:nextCondLst>
              </p:seq>
              {''.join(video_nodes)}
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
      <p:bldLst>
        {''.join(bld_nodes)}
      </p:bldLst>
    </p:timing>
    """
    slide._element.append(parse_xml(timing_xml))


def resolve_video_path(video_ref: str, video_map: dict[str, Path]) -> Path | None:
    """VID_XX またはファイルパスから正規化済みMP4パスを解決する。"""
    if video_ref in video_map:
        return video_map[video_ref]
    candidate = BASE_DIR / video_ref
    if candidate.exists():
        return candidate
    return None


def resolve_figure_path(fig_ref: str) -> Path | None:
    """静止画パスを解決する。"""
    p = Path(fig_ref)
    if p.is_absolute() and p.exists():
        return p
    for candidate in [BASE_DIR / fig_ref, BASE_DIR / "assets" / "figures" / fig_ref]:
        if candidate.exists():
            return candidate
    return None


def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """ffprobe を用いて動画の元の幅・高さ（px）を取得する。"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parts = result.stdout.strip().splitlines()[0].split("x")
    return int(parts[0]), int(parts[1])


def fit_box(
    orig_w: int,
    orig_h: int,
    box_left: Inches,
    box_top: Inches,
    box_w: Inches,
    box_h: Inches,
) -> tuple[int, int, int, int]:
    """元の縦横比を維持したまま指定枠内に収まる (left, top, width, height) を返す。"""
    if orig_w <= 0 or orig_h <= 0:
        return box_left, box_top, box_w, box_h
    scale = min(box_w / orig_w, box_h / orig_h)
    new_w = int(round(orig_w * scale))
    new_h = int(round(orig_h * scale))
    new_left = int(box_left + (box_w - new_w) / 2)
    new_top = int(box_top + (box_h - new_h) / 2)
    return new_left, new_top, new_w, new_h


def add_picture_fitted(
    slide,
    img_path: Path,
    box_left: Inches,
    box_top: Inches,
    box_w: Inches,
    box_h: Inches,
) -> None:
    """元の縦横比を維持して指定枠内に画像を中央配置する。"""
    with Image.open(img_path) as im:
        orig_w, orig_h = im.size
    left, top, width, height = fit_box(orig_w, orig_h, box_left, box_top, box_w, box_h)
    slide.shapes.add_picture(str(img_path), left, top, width=width, height=height)


def add_movie_to_slide(
    slide,
    video_path: Path,
    left: Inches,
    top: Inches,
    width: Inches,
    height: Inches,
    tmp_dir: Path,
    used_videos: set[Path],
) -> int:
    """元の縦横比を維持してスライドに動画を埋め込み、shape_id を返す。"""
    used_videos.add(video_path)
    orig_w, orig_h = get_video_dimensions(video_path)
    fit_left, fit_top, fit_w, fit_h = fit_box(orig_w, orig_h, left, top, width, height)
    poster = create_poster_image(video_path, tmp_dir)
    movie_shape = slide.shapes.add_movie(
        str(video_path),
        fit_left,
        fit_top,
        fit_w,
        fit_h,
        poster_frame_image=str(poster),
        mime_type="video/mp4",
    )
    return movie_shape.shape_id


def build_title_slide(slide, project: dict, slide_cfg: dict) -> None:
    pres = project.get("presentation", {})
    if DRAW_HEADER_BAR:
        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, sx(0), sy(0), sx(13.333), sy(7.5)
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_NAVY
        bg.line.fill.background()
        title_color = COLOR_WHITE
        sub_color = RGBColor(0xCB, 0xD5, 0xE1)
        conf_color = RGBColor(0x93, 0xC5, 0xFD)
    else:
        title_color = COLOR_NAVY
        sub_color = COLOR_MUTED
        conf_color = COLOR_ACCENT

    # 学会名
    conf_tb = slide.shapes.add_textbox(sx(0.9), sy(0.9), sx(11.5), sy(0.6))
    p = conf_tb.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = slide_cfg.get("conference", pres.get("conference", ""))
    set_run_font(r, 18, bold=True, color=conf_color)

    # 日本語演題名
    title_tb = slide.shapes.add_textbox(sx(0.9), sy(2.0), sx(11.5), sy(2.2))
    tf = title_tb.text_frame
    tf.word_wrap = True
    p_ja = tf.paragraphs[0]
    r_ja = p_ja.add_run()
    r_ja.text = slide_cfg.get("title_ja", pres.get("title_ja", ""))
    set_run_font(r_ja, 32, bold=True, color=title_color)

    # 英語演題名
    title_en = slide_cfg.get("title_en", pres.get("title_en", ""))
    if title_en:
        p_en = tf.add_paragraph()
        p_en.space_before = Pt(sf(14))
        r_en = p_en.add_run()
        r_en.text = title_en
        set_run_font(r_en, 18, bold=False, color=sub_color)

    # 演者・所属
    info_tb = slide.shapes.add_textbox(sx(0.9), sy(5.2), sx(11.5), sy(1.4))
    itf = info_tb.text_frame
    itf.word_wrap = True
    p_aff = itf.paragraphs[0]
    r_aff = p_aff.add_run()
    r_aff.text = slide_cfg.get("affiliation", pres.get("affiliation", ""))
    set_run_font(r_aff, 20, bold=False, color=title_color)

    p_pres = itf.add_paragraph()
    p_pres.space_before = Pt(sf(8))
    r_pres = p_pres.add_run()
    r_pres.text = slide_cfg.get("presenter", pres.get("presenter", ""))
    set_run_font(r_pres, 24, bold=True, color=title_color)


def build_coi_slide(slide, project: dict, slide_cfg: dict) -> None:
    coi = project.get("coi", {})
    add_header_bar(slide, slide_cfg.get("title", coi.get("slide_title", "利益相反（COI）開示")))

    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, sx(1.2), sy(2.0), sx(10.9), sy(3.6)
    )
    box.fill.solid()
    box.fill.fore_color.rgb = COLOR_LIGHT_BG
    box.line.color.rgb = COLOR_BORDER
    box.line.width = Pt(1.5)

    tb = slide.shapes.add_textbox(sx(1.6), sy(2.4), sx(10.1), sy(2.8))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = slide_cfg.get("statement_ja", coi.get("statement_ja", "")).strip()
    set_run_font(r, 26, bold=True, color=COLOR_DARK_TEXT)

    note_text = slide_cfg.get("note", coi.get("note", ""))
    if note_text:
        ntb = slide.shapes.add_textbox(sx(1.2), sy(6.0), sx(10.9), sy(0.6))
        np = ntb.text_frame.paragraphs[0]
        np.alignment = PP_ALIGN.CENTER
        nr = np.add_run()
        nr.text = note_text
        set_run_font(nr, 14, color=COLOR_MUTED)


def build_content_or_conclusion_slide(slide, slide_cfg: dict, is_conclusion: bool = False) -> None:
    title = slide_cfg.get("title", "結語" if is_conclusion else "")
    add_header_bar(slide, title, slide_cfg.get("subtitle", ""))

    bullets = slide_cfg.get("bullets", [])
    fig_ref = slide_cfg.get("figure") or slide_cfg.get("image")
    fig_path = resolve_figure_path(fig_ref) if fig_ref else None

    text_width = sx(6.8) if fig_path else sx(12.1)
    tb = slide.shapes.add_textbox(sx(0.6), sy(1.4), text_width, sy(5.3))
    tf = tb.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(sf(14))
        r = p.add_run()
        r.text = f"• {bullet}"
        set_run_font(r, 22 if is_conclusion else 20, bold=is_conclusion, color=COLOR_DARK_TEXT)

    if fig_path:
        add_picture_fitted(slide, fig_path, sx(7.7), sy(1.4), sx(5.0), sy(5.3))


def build_video_and_still_slide(
    slide, slide_cfg: dict, video_map: dict[str, Path], tmp_dir: Path, used_videos: set[Path]
) -> None:
    add_header_bar(slide, slide_cfg.get("title", ""), slide_cfg.get("subtitle", ""))

    video_ref = slide_cfg.get("video")
    still_ref = slide_cfg.get("still") or (slide_cfg.get("still_extract") or {}).get("output_fig")

    shape_ids = []
    if video_ref:
        v_path = resolve_video_path(video_ref, video_map)
        if v_path and v_path.exists():
            sid = add_movie_to_slide(
                slide, v_path, sx(0.55), sy(1.45), sx(5.9), sy(4.4), tmp_dir, used_videos
            )
            shape_ids.append(sid)

    # 左キャプション
    v_cap = slide_cfg.get("video_caption", "")
    if v_cap:
        tb = slide.shapes.add_textbox(sx(0.55), sy(5.95), sx(5.9), sy(0.6))
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = v_cap
        set_run_font(r, 15, bold=True, color=COLOR_ACCENT)

    if still_ref:
        s_path = resolve_figure_path(still_ref)
        if s_path and s_path.exists():
            add_picture_fitted(slide, s_path, sx(6.85), sy(1.45), sx(5.9), sy(4.4))

    # 右キャプション
    s_cap = slide_cfg.get("still_caption", "静止画（矢印・注釈追記用）")
    tb2 = slide.shapes.add_textbox(sx(6.85), sy(5.95), sx(5.9), sy(0.6))
    p2 = tb2.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = s_cap
    set_run_font(r2, 15, bold=True, color=COLOR_DARK_TEXT)

    enable_video_autoplay_loop(slide, shape_ids)


def build_video_grid_2x2_slide(
    slide, slide_cfg: dict, video_map: dict[str, Path], tmp_dir: Path, used_videos: set[Path]
) -> None:
    add_header_bar(slide, slide_cfg.get("title", ""), slide_cfg.get("subtitle", ""))

    items = slide_cfg.get("videos", [])[:4]
    positions = [
        (sx(0.6), sy(1.3)),
        (sx(6.85), sy(1.3)),
        (sx(0.6), sy(4.25)),
        (sx(6.85), sy(4.25)),
    ]

    shape_ids = []
    for idx, item in enumerate(items):
        left, top = positions[idx]
        if isinstance(item, dict):
            v_ref = item.get("video", "")
            label = item.get("label", "")
        else:
            v_ref = str(item)
            label = ""

        v_path = resolve_video_path(v_ref, video_map)
        if v_path and v_path.exists():
            sid = add_movie_to_slide(
                slide, v_path, left, top, sx(5.8), sy(2.5), tmp_dir, used_videos
            )
            shape_ids.append(sid)

        if label:
            tb = slide.shapes.add_textbox(left, top + sy(2.52), sx(5.8), sy(0.35))
            p = tb.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = label
            set_run_font(r, 13, bold=True, color=COLOR_DARK_TEXT)

    enable_video_autoplay_loop(slide, shape_ids)


def main() -> int:
    global SCALE_X, SCALE_Y, DRAW_HEADER_BAR

    if not PROJECT_YAML.exists() or not DECK_YAML.exists():
        print("エラー: project.yaml または slides/deck.yaml が見つかりません。")
        return 1

    with PROJECT_YAML.open("r", encoding="utf-8") as f:
        project = yaml.safe_load(f) or {}

    with DECK_YAML.open("r", encoding="utf-8") as f:
        deck = yaml.safe_load(f) or {}

    video_map: dict[str, Path] = {}
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        for v in manifest.get("videos", []):
            if "video_id" in v and "relative_path" in v:
                video_map[v["video_id"]] = BASE_DIR / v["relative_path"]

    tpl_cfg = project.get("template") or {}
    tpl_path_str = (tpl_cfg.get("path") or "").strip()
    DRAW_HEADER_BAR = bool(tpl_cfg.get("draw_header_bar", True))

    if tpl_path_str:
        tpl_path = BASE_DIR / tpl_path_str if not Path(tpl_path_str).is_absolute() else Path(tpl_path_str)
        if not tpl_path.exists():
            print(f"エラー: 指定されたテンプレート {tpl_path} が見つかりません。")
            return 1
        print(f"テンプレートを使用: {tpl_path}")
        prs = Presentation(str(tpl_path))
        clear_existing_slides(prs)
        blank_layout = select_blank_layout(prs, tpl_cfg.get("blank_layout_index"))
    else:
        prs = Presentation()
        prs.slide_width = Inches(BASE_W_IN)
        prs.slide_height = Inches(BASE_H_IN)
        blank_layout = prs.slide_layouts[6]

    SCALE_X = prs.slide_width.inches / BASE_W_IN
    SCALE_Y = prs.slide_height.inches / BASE_H_IN

    slides_cfg = deck.get("slides", [])
    total_pages = len(slides_cfg)
    used_videos: set[Path] = set()

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        for idx, slide_cfg in enumerate(slides_cfg, start=1):
            slide = prs.slides.add_slide(blank_layout)
            remove_empty_placeholders(slide)
            layout = slide_cfg.get("layout", "content")

            if layout == "title":
                build_title_slide(slide, project, slide_cfg)
            elif layout == "coi":
                build_coi_slide(slide, project, slide_cfg)
                add_footer(slide, idx, total_pages)
            elif layout == "video_and_still":
                build_video_and_still_slide(slide, slide_cfg, video_map, tmp_dir, used_videos)
                add_footer(slide, idx, total_pages)
            elif layout == "video_grid_2x2":
                build_video_grid_2x2_slide(slide, slide_cfg, video_map, tmp_dir, used_videos)
                add_footer(slide, idx, total_pages)
            elif layout == "conclusion":
                build_content_or_conclusion_slide(slide, slide_cfg, is_conclusion=True)
                add_footer(slide, idx, total_pages)
            else:
                build_content_or_conclusion_slide(slide, slide_cfg, is_conclusion=False)
                add_footer(slide, idx, total_pages)

            notes_text = slide_cfg.get("notes", "")
            if notes_text:
                slide.notes_slide.notes_text_frame.text = str(notes_text).strip()

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_PPTX))

    for v_path in sorted(used_videos):
        shutil.copy2(v_path, DIST_DIR / v_path.name)

    print(f"完了: {OUTPUT_PPTX.relative_to(BASE_DIR)} を生成しました（同梱動画: {len(used_videos)} 本）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
