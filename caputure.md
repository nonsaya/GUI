# Capture ガイド

このドキュメントでは、USB-C 接続のビデオキャプチャーデバイスをGUIで表示する手順をまとめます。

## 動作確認環境
- OS: Ubuntu 22.04 (linux 6.8)
- Python: 3.10
- PyQt6/Qt6: 6.5.3（ABI不整合回避のため固定）
- OpenCV: 4.9.0.80

## デバイスの確認
```
ls -1 /dev/video*
```
`/dev/video2` でプレビューができることを確認。

## 依存インストール
```
pip3 install --user -r requirements.txt
```

## 起動方法
リポジトリ直下で実行:
```
cd /home/nonsaya-x/repo/gui
python3 -m src.gui.app
```
または任意ディレクトリから:
```
PYTHONPATH=/home/nonsaya-x/repo/gui python3 -m src.gui.app
```

## トラブルシュート
- PyQt6 読み込み時の `undefined symbol ... Qt_6` エラー: PyQt6/Qt6 を 6.5.3 に固定。
- 開けないデバイスがある場合: `/dev/video0`〜`/dev/video3` を順に選択し、利用可能なものを使用。


> NOTE: 最新のドキュメントは CAPTURE.md を参照してください。
