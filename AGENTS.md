# CVIT症例報告プレゼンテーション自動構築プロジェクト (AGENTS.md)

## 1. 絶対遵守ルール（個人情報保護・メディアアクセス制限）
- **バイナリ動画・プレビュー画像の読み込み禁止**:
  - `raw_inputs/raw_videos/`、`raw_inputs/frame_previews/`、`assets/videos_normalized/` 内の動画ファイルおよびプレビュー画像ファイルをAIは直接読み込まないこと（`.geminiignore` でも制限）。
  - 動画の把握には必ずテキストメタデータである `assets/video_manifest.json` のみを参照すること。
- **個人特定情報（PII）の記載禁止**:
  - 患者氏名、患者ID（カルテ番号）、生年月日、具体的な手術日・検査日（例: `2026年11月19日` など）は、`raw_inputs/notes.md`、`slides/deck.yaml`、`presentation.pptx`、スピーカーノート等いかなるファイルにも記載しないこと。
  - 年齢は「70歳代」、経過は「術後第3病日」「術後6か月」のように相対表現を使用すること。

## 2. プロジェクト構成
- `project.yaml`: 演題名（日英）、演者、所属、CVIT規定COI文言
- `skills/cvit-case-report/SKILL.md`: 医師への構造化ヒアリングおよび `deck.yaml` 生成手順
- `scripts/01_normalize_videos.py`: 動画の正規化（H.264/30fps/幅1280px/音声なし）、1秒ごとのプレビュー画像生成、`assets/video_manifest.json` 出力
- `scripts/02_extract_stills.py`: 指定秒数からの高解像度PNG静止画抽出（`assets/figures/`）
- `scripts/03_build_slides.py`: 16:9 PowerPoint生成およびUSB持ち込み用パッケージ（`dist/CVIT_Presentation_USB/`）構築

## 3. 実行パイプライン（チャット依頼でAIが自動実行可）
ユーザーからチャットで依頼された場合（例：「動画を入れたので進めて」「スライドを生成して」）、AIはバイナリ動画・画像を直接読み込まないルールを厳守しつつ、以下のコマンドを `.venv/bin/python` で代行実行すること。
0. **動画正規化**: 医師が `raw_inputs/raw_videos/` に元動画を配置したあと、`.venv/bin/python scripts/01_normalize_videos.py` を実行して `assets/video_manifest.json` と `raw_inputs/frame_previews/` を生成する。
1. **ヒアリング**: `skills/cvit-case-report/SKILL.md` に従い、`assets/video_manifest.json` を読み込んだ上で医師へ4項目の質問を行う。
2. **メタデータ・ノート更新**: 医師の回答をもとに `raw_inputs/notes.md` を作成・更新し、`assets/video_manifest.json` の `clinical_label` や `selected_stills` を更新する。
3. **スライド設計 (`slides/deck.yaml`)**: `skills/cvit-case-report/SKILL.md` のルールに従い、全8〜9枚の `slides/deck.yaml` を生成する。
4. **静止画抽出**: `.venv/bin/python scripts/02_extract_stills.py` を実行し、`assets/figures/` に高解像度PNGを出力する。
5. **PPTX・USBパッケージ生成**: `.venv/bin/python scripts/03_build_slides.py` を実行し、`dist/CVIT_Presentation_USB/presentation.pptx` および同梱MP4一式を生成する。
