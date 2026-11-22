# CVIT 症例報告プレゼンテーション自動構築ツール

日本心血管インターベンション治療学会（CVIT）向けの症例報告スライド（16:9 PowerPoint）を、症例動画の正規化・静止画切り出し・AIヒアリングによる構成設計・発表原稿付きPPTX生成まで一気通貫で自動構築するローカルツールです。

---

## 主な特徴

- **個人情報保護（Privacy by Design）**
  - [`.geminiignore`](.geminiignore) と [`AGENTS.md`](AGENTS.md) により、AIは元動画・正規化動画・プレビュー画像を一切読み込まず、テキストメタデータ（`assets/video_manifest.json`）のみを参照します。
  - 患者氏名・ID・生年月日・具体的な手術日（PII）を排除した相対表現でのスライド生成を徹底します。
- **会場PCで確実に再生できる動画正規化＆埋め込み**
  - `ffmpeg` で H.264（`yuv420p`）/ 30fps / 幅1280px / 音声なし MP4 に変換し、元の縦横比（1:1、4:3、16:9等）を維持したままPPTX内に完全埋め込みします。
  - OpenXML（`p:timing`）により、スライド表示時の**自動再生・無限ループ・ミュート**を自動設定します。
- **1秒毎プレビューからの高解像度静止画抽出**
  - 医師が `raw_inputs/frame_previews/` のサムネイルから秒数を指定するだけで、矢印・注釈追記用の高解像度PNGを自動抽出・配置します。
- **テンプレートの簡単切り替え**
  - [`project.yaml`](project.yaml) の `template.path` を書き換えるだけで、医局・病院ロゴ入りなどの `.pptx` テンプレートに差し替え可能です。

---

## ディレクトリ構成

```text
.
├── AGENTS.md                       # AI遵守ルール（PII・バイナリ読み込み禁止等）
├── .geminiignore                   # 動画・画像ファイルのAIアクセス制限
├── README.md                       # 本ドキュメント
├── DEMO_SCENARIO.md                # ライブデモ用シナリオ
├── requirements.txt                # Python依存パッケージ
├── project.yaml                    # 演題情報・COI文言・テンプレート設定
├── skills/
│   └── cvit-case-report/
│       └── SKILL.md                # AIによる医師への構造化ヒアリング手順
├── templates/                      # PowerPointテンプレート（.pptx）格納先
├── raw_inputs/
│   ├── raw_videos/                 # 元動画配置フォルダ（.mp4/.avi/.mov/.wmv/.mkv/.mpg）
│   ├── frame_previews/             # 1秒毎サムネイルJPG（医師確認用）
│   └── notes.md                    # ヒアリング内容の症例メモ
├── assets/
│   ├── videos_normalized/          # 正規化済みMP4（VID_01.mp4〜）
│   ├── figures/                    # 抽出された高解像度静止画PNG
│   └── video_manifest.json         # AIが参照する動画メタデータ
├── slides/
│   └── deck.yaml                   # スライド構成・原稿定義（全8〜9枚）
├── scripts/
│   ├── 01_normalize_videos.py      # 動画正規化・プレビュー生成・manifest出力
│   ├── 02_extract_stills.py        # 指定秒数からの静止画PNG抽出
│   └── 03_build_slides.py          # 16:9 PPTX生成・USBパッケージ出力
└── dist/
    └── CVIT_Presentation_USB/      # 提出・持ち込み用出力（presentation.pptx＋予備MP4）
```

---

## Mac での環境構築手順（GitHub から取得〜Antigravity で開く）

### 1. リポジトリの取得と Antigravity で開く

#### 方法A：Antigravity IDE の画面から直接クローンする（`git` コマンド不要）
1. **Antigravity IDE** を起動します。
2. 起動画面（Welcome）の **「Clone Git Repository...」** をクリックします（または `⌘ + Shift + P` でコマンドパレットを開き、**`Git: Clone`** を選択します）。
3. GitHub リポジトリの URL を入力し、保存先フォルダを選択します。
4. クローン完了後、右下の通知から **「Open」** をクリックしてプロジェクトを開きます。

#### 方法B：ターミナルからクローンして開く
```bash
git clone <リポジトリURL>
cd cvit-slide
```
クローン後、Antigravity の **「Open Folder」** から `cvit-slide` フォルダを開きます。

---

プロジェクトを開くと、ルートにある [`AGENTS.md`](AGENTS.md)（個人情報保護・実行ルール）と [`.geminiignore`](.geminiignore)（動画・画像の読み込み制限）が自動で有効になります。

### 2. 前提ツール（ffmpeg / Python 3）と Python 仮想環境のセットアップ（チャットで完結）

フォルダを開いたら、**Antigravity のチャット** で次のように依頼するだけで、環境確認からパッケージ導入まで自動実行できます（ターミナル操作は不要です）。

> 「Mac の環境構築（`ffmpeg` / `python3` の確認・導入と、`.venv` 仮想環境への `requirements.txt` インストール）を実行してください」

<details>
<summary>手動でターミナルからセットアップする場合のコマンド</summary>

1. **前提ツールのインストール（Homebrew / Python 3 / ffmpeg）**
   ```bash
   # Homebrew が未導入の場合（必要な場合のみ）
   # /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   brew install ffmpeg python3
   python3 --version
   ffmpeg -version | head -n 1
   ```

2. **Python 仮想環境の作成とパッケージインストール**
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -r requirements.txt
   ```

</details>

これで環境構築は完了です（利用イメージや進行例は [`DEMO_SCENARIO.md`](DEMO_SCENARIO.md) もあわせてご参照ください）。

---

## 本番運用のワークフロー（チャットだけで完結）

新しい症例を作成する際は、動画をフォルダに入れるだけで **Step 0〜5 まですべて Antigravity のチャットへの依頼** で進められます（ターミナル操作は不要です）。

0. **元動画の配置と正規化**
   - Finder 等で `raw_inputs/raw_videos/` に元動画ファイルを入れます。
   - Antigravity のチャットで次のように依頼します：
     > 「`raw_inputs/raw_videos/` に動画を入れたので、正規化してヒアリングを始めてください」
   - AI が内部で `01_normalize_videos.py` を実行し、動画の変換・1秒毎プレビュー生成・`assets/video_manifest.json` 作成を行います。
1. **AIによるヒアリング**
   - AI が検出された動画一覧を提示し、4項目（動画内容・切り出し秒数・Take-home message・患者背景/経過）に加えて、**演題名（日英）** と [`project.yaml`](project.yaml) の基本情報（演者・所属・学会名・COI）に変更があるかを確認します。
2. **メタデータ・演題情報更新**
   - チャットで回答を伝えると、AI が `raw_inputs/notes.md`・`assets/video_manifest.json`・（必要に応じ）[`project.yaml`](project.yaml) を更新します。
   - 演者・所属・COI などはあらかじめ [`project.yaml`](project.yaml) にご自身の正しい情報を記入しておけば、以降はそのまま流用されます。
3. **スライド設計（`slides/deck.yaml`）**
   - AI が全8〜9枚の `slides/deck.yaml`（発表時間配分付き日本語スピーカーノート含む）を生成します。
4. **静止画抽出 ＆ 5. PPTX・USBパッケージ生成**
   - チャットで次のように依頼します（または Step 3 の流れでそのまま実行されます）：
     > 「静止画を抽出して、PowerPoint（presentation.pptx）を生成してください」
   - AI が `02_extract_stills.py` と `03_build_slides.py` を自動実行し、`dist/CVIT_Presentation_USB/presentation.pptx`（MP4完全埋め込み済み）を出力します。

> **※手動で実行したい場合**: ターミナルから `.venv/bin/python scripts/01_normalize_videos.py`、`02_extract_stills.py`、`03_build_slides.py` を個別に実行することも可能です。

---

## テンプレートのカスタマイズ方法

[`project.yaml`](project.yaml) の `template` セクションを変更することで、任意の PowerPoint テンプレートに切り替えられます。

```yaml
template:
  # templates/ フォルダに .pptx を配置してパスを指定（空欄にすると標準の白紙デザインを使用）
  path: "templates/my_template.pptx"
  # テンプレート側の表紙・本文デザインをそのまま活かす場合は false に設定
  draw_header_bar: false
  # 必要に応じてレイアウト番号を明示指定（省略時は自動選択）
  # title_layout_index: 0
  # blank_layout_index: 6
```

- **2レイアウト構成（表紙＋本文）**: テンプレートからは **表紙用（`Title Slide` 等）** と **本文用（`Blank` / `白紙` 等）** の2つのレイアウトのみを使用します。テンプレート側のプレースホルダー配置に依存しないため、医局・病院のテンプレートをそのまま流用しやすい設計です。
- **表紙の自動保護**: テンプレートに専用の表紙レイアウトが無い場合でも、表紙には本文用ヘッダー帯が重ならないよう自動でカバー背景を描画します。
- テンプレート内の既存スライドはビルド時に自動削除され、スライドサイズに合わせてレイアウト・フォント・動画サイズが自動スケーリングされます。

---

## 別の症例を新しく作成する場合（前回データのクリア）

1つの症例発表を作成したあと、別の症例で最初からやり直したい場合は、以下のコマンドで前回の動画・中間ファイル・出力をリセットできます（スクリプトやテンプレート設定はそのまま残ります）。

```bash
rm -rf raw_inputs/raw_videos/* raw_inputs/frame_previews/* \
       assets/videos_normalized/* assets/figures/* \
       dist/CVIT_Presentation_USB/* \
       raw_inputs/notes.md assets/video_manifest.json slides/deck.yaml
```
