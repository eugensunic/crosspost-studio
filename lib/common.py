"""Shared helpers: config, link block, slugs, UTM, Ollama calls."""
from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILE = os.environ.get("PROFILE", "tom")


def load_config() -> dict:
    with open(ROOT / "profiles" / PROFILE / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


CFG = load_config()


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].rstrip("-")


def utm(url: str, network: str, mode: str) -> str:
    if not CFG.get("utm") or "REPLACE" in url:
        return url
    sep = "&" if "?" in url else "?"
    return url + sep + urlencode({"utm_source": network, "utm_medium": "social", "utm_campaign": mode})


def link_block(network: str = "site", mode: str = "video", lang: str = "en") -> str:
    L = CFG["links"]
    labels = [
        ("tomsunic.com", L["site"]),
        ("Substack", L["substack"]),
        ("Ko-fi", L["kofi"]),
        ("Books", L["books"]),
        (f"PayPal {L['paypal']} · IBAN {L['iban']}", None),
        ("X", L["x"]),
        ("LinkedIn", L["linkedin"]),
        ("Facebook", L["facebook"]),
        ("Telegram", L["telegram"]),
    ]
    lines = []
    for label, url in labels:
        lines.append(label if url is None else f"{label}: {utm(url, network, mode)}")
    return "\n".join(lines)


def closing_line(lang: str) -> str:
    return CFG["closing_line"].get(lang, CFG["closing_line"]["en"])


def ollama(prompt: str, system: str = "", model: str | None = None, json_mode: bool = False) -> str:
    """Call the local Ollama server. Free, no key."""
    import urllib.request

    body = {
        "model": model or CFG["ollama"]["model"],
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if json_mode:
        body["format"] = "json"
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["response"].strip()


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(map(str, cmd)))
    return subprocess.run(cmd, check=True, **kw)


def read_json(p: Path | str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path | str, data) -> None:
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
