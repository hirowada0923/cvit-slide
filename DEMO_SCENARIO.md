# CVIT症例報告プレゼンテーション自動構築 デモシナリオ

本ドキュメントは、現在のテスト用データ（`raw_inputs/`・`assets/`・`slides/deck.yaml`・`dist/`）をそのまま活用し、本システムの価値とワークフローを実演するためのデモ手順書です。

---

## 1. デモでアピールする3つのポイント
1. **個人情報保護（Privacy by Design）**
   - [`.geminiignore`](.geminiignore) と [`AGENTS.md`](AGENTS.md) により、AIは生動画・正規化動画・プレビュー画像を一切読み込まず、テキストメタデータ（[`assets/video_manifest.json`](assets/video_manifest.json)）のみを参照する。
   - 患者氏名・ID・生年月日・具体的手術日（PII）を排除した相対表現を徹底する。
2. **医師の負担を最小化する対話型ヒアリング**
   - [`skills/cvit-case-report/SKILL.md`](skills/cvit-case-report/SKILL.md) に従い、AIが4項目を構造化ヒアリングして発表原稿（時間配分付き）まで含む [`slides/deck.yaml`](slides/deck.yaml) を設計する。
3. **会場Windows PCで確実に動くUSBパッケージ出力**
   - `ffmpeg` で H.264 / yuv420p / 30fps / 幅1280px / 音声なし MP4 に自動変換し、OpenXML で自動再生・無限ループを設定した PowerPoint と同梱 MP4 一式を [`dist/CVIT_Presentation_USB/`](dist/CVIT_Presentation_USB/) に出力する。

---

## 2. 現在のデモ用データ構成
- **元動画**: `raw_inputs/raw_videos/media1.mp4` 〜 `media8.mp4`（8本）
- **正規化動画**: `assets/videos_normalized/VID_01.mp4` 〜 `VID_08.mp4`
- **1秒毎プレビュー**: `raw_inputs/frame_previews/VID_01/` 〜 `VID_08/`（医師が切り出し秒数を選ぶ用）
- **動画メタデータ**: [`assets/video_manifest.json`](assets/video_manifest.json)
- **症例メモ**: [`raw_inputs/notes.md`](raw_inputs/notes.md)
- **スライド設計**: [`slides/deck.yaml`](slides/deck.yaml)（全9枚）
- **抽出静止画**: `assets/figures/fig_vid01_cag.png`, `fig_vid04_ofdi.png`, `fig_vid06_day8_pci.png`, `fig_vid07_final.png`
- **完成パッケージ**: [`dist/CVIT_Presentation_USB/presentation.pptx`](dist/CVIT_Presentation_USB/presentation.pptx) ＋ 同梱MP4 6本

---

## 3. ライブデモ手順

### パターンA：短時間デモ（約3分：パイプライン実行＆PPTX確認）
1. **プライバシー設計の紹介**
   - [`.geminiignore`](.geminiignore) と [`assets/video_manifest.json`](assets/video_manifest.json) をエディタで開き、「AIには動画本体は見せず、秒数とラベルだけを認識させる」ことを説明する。
2. **YAML設計と静止画・スライド一括生成の実演**
   - [`slides/deck.yaml`](slides/deck.yaml) を見せ、数行のYAMLでレイアウト（`video_grid_2x2`, `video_and_still` 等）と静止画切り出し秒数、時間配分付き原稿を定義していることを示す。
   - ターミナルで以下を実行する：
     ```bash
     .venv/bin/python scripts/02_extract_stills.py && .venv/bin/python scripts/03_build_slides.py
     ```
3. **完成スライドのプレゼンモード確認**
   - `dist/CVIT_Presentation_USB/presentation.pptx` を PowerPoint で開き、スライドショーを実行する。
   - **確認ポイント**：
     - 3枚目：CAG 2×2 グリッドの同時自動ループ再生
     - 4・6・8枚目：左の動画自動ループ＋右の高解像度静止画（矢印追記用）
     - 発表者ツール（またはノート欄）：各スライドの目安時間・累計時間付き日本語原稿

---

### パターンB：対話デモ（約5〜10分：AIヒアリングからの編集体験）
1. **プレビュー確認の提示**
   - Finder等で `raw_inputs/frame_previews/VID_06/` を開き、「医師はこの1秒毎のサムネイルを見て秒数を指定する」流れを見せる。
2. **AIへの指示例**
   - チャットで次のように入力し、対話からスライドを修正・再ビルドする様子を実演する：
     > `skills/cvit-case-report/SKILL.md` に従って、`slides/deck.yaml` の6枚目の静止画切り出し秒数を `VID_06` の `8.0` 秒に変更し、静止画再抽出とPPTX再生成を実行してください。
3. **再生成結果の確認**
   - `02_extract_stills.py` と `03_build_slides.py` が走り、`presentation.pptx` が即座に更新されることを確認する。

---

## 4. デモ終了後・本番症例への切り替え手順
本番のCD動画を投入する際は、以下のコマンドでテスト用メディア・成果物をクリーンアップしてください（スクリプト・スキル・設定ファイルはそのまま残ります）。

```bash
rm -rf raw_inputs/raw_videos/* raw_inputs/frame_previews/* \
       assets/videos_normalized/* assets/figures/* \
       dist/CVIT_Presentation_USB/* \
       raw_inputs/notes.md raw_inputs/extracted_pptx_summary.json \
       assets/video_manifest.json slides/deck.yaml
```
その後、本番動画を `raw_inputs/raw_videos/` に配置し、`.venv/bin/python scripts/01_normalize_videos.py` から開始してください。
