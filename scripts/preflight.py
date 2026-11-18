"""Deploy se pehle settings check. Usage: python -m scripts.preflight [--env-file .env]"""
import os
import sys
from pathlib import Path

REQUIRED = ["GEMINI_API_KEY", "API_KEY", "AUTH_SECRET", "DASHBOARD_PASSWORD", "DATABASE_URL"]


def parse_env_file(path) -> dict:
    values = {}
    p = Path(path)
    if not p.exists():
        return values
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def check_env(env: dict) -> list[tuple[str, str]]:
    results = []
    for name in REQUIRED:
        if not env.get(name):
            results.append(("FAIL", "%s set nahi hai" % name))
    secret = env.get("AUTH_SECRET", "")
    if secret and len(secret) < 32:
        results.append(("FAIL", "AUTH_SECRET 32 characters se chhota hai"))
    if not (env.get("EMAIL_PASSWORD") or env.get("RESEND_API_KEY")):
        results.append(("FAIL", "EMAIL_PASSWORD ya RESEND_API_KEY set nahi hai"))
    if env.get("DEBUG", "").lower() == "true":
        results.append(("WARN", "DEBUG=true hai, production me false rakhein"))
    if env.get("TRUST_PROXY_HEADERS", "").lower() != "true":
        results.append(("WARN", "TRUST_PROXY_HEADERS=true nahi hai (Render par true chahiye)"))
    return results


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    env = dict(os.environ)
    if "--env-file" in args:
        env.update(parse_env_file(args[args.index("--env-file") + 1]))
    results = check_env(env)
    for level, msg in results:
        print("[%s] %s" % (level, msg))
    failed = sum(1 for level, _ in results if level == "FAIL")
    if not results:
        print("Sab settings theek hain.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
