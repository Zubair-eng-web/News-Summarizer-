import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip"}
PATTERNS = {
    "Google/Gemini API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "GitHub token": re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}"),
    "Resend API key": re.compile(r"\bre_[0-9A-Za-z]{6,}_[0-9A-Za-z]{16,}\b"),
    "Telegram bot token": re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    "Private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def find_secrets(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if pattern.search(text)]


def tracked_files():
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [ROOT / line for line in out.splitlines() if line]


def test_detector_finds_fake_secrets():
    assert find_secrets("key=AIza" + "a" * 35) == ["Google/Gemini API key"]
    assert find_secrets("ghp_" + "b" * 36) == ["GitHub token"]
    assert find_secrets("123456789:" + "c" * 35) == ["Telegram bot token"]
    assert find_secrets("-----BEGIN " + "PRIVATE KEY-----") == ["Private key"]
    assert find_secrets("GEMINI_API_KEY=your_gemini_api_key_here") == []


def test_no_secrets_in_tracked_files():
    files = tracked_files()
    if files is None:
        pytest.skip("git maujood nahi")
    problems = []
    for path in files:
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name in find_secrets(text):
            problems.append(f"{path.relative_to(ROOT)}: {name}")
    assert problems == []


def test_env_and_database_files_are_not_tracked():
    files = tracked_files()
    if files is None:
        pytest.skip("git maujood nahi")
    bad = [p.name for p in files if p.name == ".env" or p.suffix == ".db"]
    assert bad == []