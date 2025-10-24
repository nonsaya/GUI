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

