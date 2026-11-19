---
name: cvit-case-report
description: CVIT（日本心血管インターベンション治療学会）症例報告プレゼンテーション作成のための構造化ヒアリングと slides/deck.yaml 生成ガイド
---

# CVIT症例報告ヒアリング＆スライド設計スキル

## 1. 事前確認とプライバシー厳守
- 必ず `assets/video_manifest.json`（テキストメタデータ）のみを読み込むこと。
- `raw_inputs/raw_videos/`、`raw_inputs/frame_previews/`、`assets/videos_normalized/` 内の画像・動画ファイルは絶対に読み込まないこと。
- 患者氏名、ID、生年月日、具体的な手術日などの個人特定情報（PII）は質問・記録・スライド生成のいずれにも含めないこと。
- ユーザーから「動画を入れたので進めて」「正規化して」「スライドを作成して」とチャットで依頼された場合は、`.venv/bin/python scripts/01_normalize_videos.py`、`02_extract_stills.py`、`03_build_slides.py` をAIが直接実行して完結させること（ユーザーに手動のターミナル操作を求めない）。

## 2. 医師への構造化ヒアリング（4項目）
`assets/video_manifest.json` に登録されている動画一覧（`video_id`, `original_name`, `duration_sec`）を医師に提示し、以下の4点を簡潔に質問する：

1. **検出された動画（VID_01〜）の内容と使用デバイス・手技の流れ**
   - 各動画がどのフェーズ（例：術前CAG、IVUS/OCT、バルーン拡張/Rotablator/IVL、最終造影など）か、使用した主要デバイス名（サイズ・種類）を確認する。
2. **静止画切り出し指定（`raw_inputs/frame_previews/` 参照）**
   - 医師にローカルの `raw_inputs/frame_previews/VID_XX/` の1秒ごとサムネイルを確認してもらい、静止画として切り出したい秒数を指定してもらう（例：「VID_01の2.5秒」「VID_02の4.0秒」）。
3. **一番の売り（Take-home message）**
   - 本症例で最も伝えたい工夫・教訓・新規性（1〜2文）。
4. **患者背景・術前検査・術後経過（個人特定情報なし）**
   - 年代・性別、主訴・既往歴、術前検査所見（心電図・心エコー・採血等）、術後経過・転帰。

## 3. メタデータとノートの更新
医師からの回答を受け取ったら、以下を更新・作成する：
- `raw_inputs/notes.md`: 回答内容を整理した症例メモ（PII除外）。
- `assets/video_manifest.json`: 各動画の `clinical_label`（例: `"Pre-PCI CAG (LAO cranial)"`）と `selected_stills`（例: `[{"timestamp_sec": 2.5, "output_fig": "fig_vid01_2_5s.png", "caption": "高度狭窄部"}]`）を更新。

## 4. `slides/deck.yaml` 生成ルール
`project.yaml` の演題情報と合わせ、**全8〜9枚** の構成で `slides/deck.yaml` を生成する。

### 推奨スライド構成（8〜9枚）
1. **1枚目 (`layout: title`)**: タイトルスライド（`project.yaml` 連携）
2. **2枚目 (`layout: coi`)**: CVIT規定COI開示スライド（`project.yaml` 連携）
3. **3枚目 (`layout: content`)**: 患者背景・現病歴・術前検査
4. **4枚目 (`layout: video_and_still` または `video_grid_2x2`)**: 初回造影・病変評価（CAG動画＋静止画、またはCAG/IVUS/OCT 2x2グリッド）
5. **5枚目 (`layout: content`)**: 治療戦略と使用デバイス
6. **6枚目 (`layout: video_and_still`)**: 手技のポイント・デバイス通過/拡張（動画ループ＋矢印追記用静止画）
7. **7枚目 (`layout: video_and_still` または `video_grid_2x2`)**: 最終造影・治療結果（Final CAG / Final IVUS/OCT）
8. **8枚目 (`layout: content`)**: 術後経過・考察（文献的考察や工夫点）
9. **最終スライド (`layout: conclusion`)**: 結語（Take-home message）

### `slides/deck.yaml` 記載仕様
- 全スライドに `notes` フィールドを設け、**発表時間配分（例：`【目安：0:30 / 累計 1:30】`）付きの日本語発表原稿**を記載する（合計発表時間はCVIT一般演題・症例報告の標準である5〜7分程度を目安に配分）。
- 静止画の切り出しが必要な箇所には、`still_extract`（または `stills`）として `extract_from`（`VID_XX`）、`timestamp_sec`、`output_fig`（例：`assets/figures/fig_01.png`）を明記し、`02_extract_stills.py` で自動抽出できるようにする。
- 使用可能な `layout` 値：`title`, `coi`, `video_and_still`, `video_grid_2x2`, `content`, `conclusion`。
