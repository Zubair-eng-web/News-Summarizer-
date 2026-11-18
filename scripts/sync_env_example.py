"""Settings aur .env.example ko barabar rakhta hai.

python -m scripts.sync_env_example          # missing keys .env.example me jod deta hai
python -m scripts.sync_env_example --check  # sirf check (missing ho to exit code 1)
"""
import sys
from pathlib import Path

from app.core.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"
SECRET_SUFFIXES = ("_key", "_password", "_secret", "_token")


def existing_keys(text: str) -> set[str]:
    keys = set()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip().upper())
    return keys


def default_text(name: str, value) -> str:
    if name.endswith(SECRET_SUFFIXES):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def missing_lines(text: str | None = None, settings_cls=Settings) -> list[str]:
    if text is None:
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
    have = existing_keys(text)
    lines = []
    for name, field in settings_cls.model_fields.items():
        if name.upper() in have:
            continue
        value = "" if field.is_required() else field.get_default(call_default_factory=True)
        lines.append(f"{name.upper()}={default_text(name, value)}")
    return lines


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not ENV_EXAMPLE.exists():
        print(".env.example nahi mili")
        return 1
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    lines = missing_lines(text)
    if not lines:
        print("Sab settings .env.example me maujood hain")
        return 0
    print("Missing:", ", ".join(line.split("=")[0] for line in lines))
    if "--check" in args:
        return 1
    addition = "\n# Auto-added by scripts.sync_env_example\n" + "\n".join(lines) + "\n"
    ENV_EXAMPLE.write_text(text.rstrip("\n") + "\n" + addition, encoding="utf-8")
    print(f"{len(lines)} settings .env.example me jod di gayin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())