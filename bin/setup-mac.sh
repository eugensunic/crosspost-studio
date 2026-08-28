#!/usr/bin/env bash
# One-time Mac setup for the prep tools (GPU side of the pipeline).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v brew >/dev/null || { echo "install Homebrew first: https://brew.sh"; exit 1; }
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list ollama >/dev/null 2>&1 || brew install ollama
brew list uv >/dev/null 2>&1 || brew install uv

# Python 3.11/3.12 venv — mlx-whisper and captacity do not support 3.14 yet.
uv venv --python 3.12 "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
uv pip install -r "$ROOT/requirements.txt"

brew services start ollama || true
MODEL="$(python3 -c "import yaml;print(yaml.safe_load(open('$ROOT/profiles/tom/config.yaml'))['ollama']['model'])")"
ollama pull "$MODEL"

# Pre-download the Whisper model (≈1.6 GB) so the first run is not slow.
python3 - <<'EOF'
import mlx_whisper, yaml
m = yaml.safe_load(open("profiles/tom/config.yaml"))["whisper"]["model"]
print("whisper model:", m)
EOF

[ -f "$ROOT/.env" ] || cp "$ROOT/.env.example" "$ROOT/.env"
chmod +x "$ROOT"/bin/*.sh "$ROOT"/lib/*.py
echo
echo "Done. Next:"
echo "  1. edit profiles/tom/config.yaml (links, Postiz URL, integration IDs)"
echo "  2. edit .env (POSTIZ_KEY, optional SUBSTACK_*)"
echo "  3. source .venv/bin/activate && bin/publish.sh --mode video test.mp4 \"Test\" --dry-run"
