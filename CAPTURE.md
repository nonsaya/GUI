# CAPTURE ガイド（GStreamer + MP4/30fps）

## 概要
- USB-C/HDMI キャプチャを GUI でプレビュー／録画／再生
- 既定デバイス: `/dev/video0`
- バックエンド: GStreamer（環境変数 `USE_GST=1`）/ OpenCV を切替
- 録画: MP4(H.264) 固定、常に 30fps で出力（不足フレームは内部で補間/重複）
- 再生: GUI内の再生コントロール（Play/Pause/Stop/Seek/0.5x/1x/2x）

## セットアップ
### 依存（Ubuntu）
```bash
sudo apt update && sudo apt install -y \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
  python3-gi gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0
```

## 起動
- GStreamer バックエンドで起動:
```bash
cd /home/nonsaya-x/repo/gui
USE_GST=1 python3 -m src.newapp.main
```

## 使い方
- デバイス: 既定で `/dev/video0` が選択。必要に応じて変更して `Start`。
- 録画: `Rec` → ファイル名（MP4のみ）→ `Stop Rec`
  - 出力は常に 30fps（VLC のプロパティで確認可能）
- 再生: `Open File` → Play/Pause/Stop、スライダーでシーク、速度は `0.5x/1x/2x`

### RViz2（外部ウィンドウ表示）
- GUI上部にある `Start RViz2` / `Stop RViz2` / `Attach` ボタンのみで操作します。
- RViz2は外部ウィンドウとして起動します（Wayland/Xorg どちらでも外部表示）。

### SSH ターミナル
- HostName / User / Port を入力し、必要に応じて Identity file（例: `~/.ssh/id_ed25519`）または Password を設定して `Connect`。
- 接続後、下部の入力欄でコマンドを入力して Enter。出力は上のテキストエリアに追記されます。
- プロンプト（`user@host:`）部分のみ緑色で強調表示されます。

## 推奨設定（滑らかさ優先）
- デバイスを 1920x1080@30 もしくは 1280x720@30 に固定
```bash
# MJPEG が使える場合（帯域に余裕）
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=MJPG --set-parm=30
# MJPEG が使えない場合（NV12で720p/30）
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=NV12 --set-parm=30
```

## トラブルシュート
- 何も映らない: 下記で疎通確認
```bash
gst-launch-1.0 -v v4l2src device=/dev/video0 ! videoconvert ! video/x-raw,format=BGR ! fakesink sync=false
```
- 早送りに見える: 保存ファイルは 30fps 固定。GUI内再生はファイルFPSを取得できない環境では 30fps でスロットリング。
- RViz2 埋め込み: Xorg 推奨（Waylandは外部ウィンドウ）

## 備考
- 背景: ダークグレー、ボタン: 白文字のダークテーマ
- バックエンド切替: `USE_GST=1`（GStreamer）／未設定（OpenCV）
