# GUI

USB-C 経由のビデオキャプチャをGUIで表示するMVP。

## 使い方

- 依存インストール（仮想環境未使用）:

  pip3 install --user -r requirements.txt

- 起動:

  python3 -m src.gui.app

- 仮想環境を使う場合:

  sudo apt install -y python3.10-venv
  python3 -m venv .venv && source .venv/bin/activate
  pip install -U pip && pip install -r requirements.txt
  python -m src.gui.app


### 新GUIアプリ

リポジトリ直下で実行:

  python3 -m src.newapp.main


## Windows の実行手順

- 依存インストール（推奨: 仮想環境）
  python -m venv .venv && .\.venv\Scripts\activate
  pip install -U pip && pip install -r requirements.txt

- 起動
  python -m src.newapp.main

- デバイス選択
  コンボボックスに検出されたカメラ（DirectShow/MSMF）が表示されます。
  開けない場合は別のエントリを選択してください。


## RViz2 埋め込み (Linux/X11)

- 前提: rviz2, wmctrl がインストール済み、Xorg (Wayland不可)
- 起動: 新GUIの "RViz2" タブで "Start RViz2"
- 停止: "Stop RViz2"
- 失敗時: 外部ウィンドウとして起動します（埋め込めない場合）


### GStreamer バックエンドを使う

依存インストール（Ubuntu）:

  sudo apt update && sudo apt install -y \
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    python3-gi gir1.2-gst-1.0

起動（GStreamer使用）:

  USE_GST=1 python3 -m src.newapp.main

