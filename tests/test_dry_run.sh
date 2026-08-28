#!/usr/bin/env bash
# Offline smoke test: fakes meta.json and runs postiz.py --dry-run + site_post.py into a temp site repo.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT/lib"
W="$ROOT/work/test-dry"; rm -rf "$W"; mkdir -p "$W"
cat > "$W/meta.json" <<'EOF'
{"spoken":"hr","slug":"test-video","bilingual_title":"Testni naslov · Test title",
 "hr":{"title":"Testni naslov","description":"Opis.","summary":"Sažetak.","x":"x","linkedin":"li","hashtags":["test"]},
 "en":{"title":"Test title","description":"Desc.","summary":"Summary.","x":"x","linkedin":"li","hashtags":["test"]},
 "chapters":[{"t":"00:00","label":"Uvod"}]}
EOF
printf '1\n00:00:00,000 --> 00:00:02,000\nDobar dan.\n' > "$W/hr.srt"
printf '1\n00:00:00,000 --> 00:00:02,000\nGood day.\n' > "$W/en.srt"
"${PYTHON:-python3}" "$ROOT/lib/postiz.py" --work "$W" --mode video --dry-run
TMPSITE="$(mktemp -d)"
"${PYTHON:-python3}" - "$W" "$TMPSITE" <<'EOF'
import sys, os
sys.path.insert(0, os.environ["PYTHONPATH"])
import common; common.CFG["site"]["repo"] = sys.argv[2]
import site_post; sys.argv = ["site_post", "--work", sys.argv[1], "--mode", "video", "--video-id", "dQw4w9WgXcQ"]
site_post.main()
EOF
echo "--- rendered page ---"; cat "$TMPSITE"/docs/posts/test-video.md | head -30
echo; echo "OK"
