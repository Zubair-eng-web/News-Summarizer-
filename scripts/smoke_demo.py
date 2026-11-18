"""Smoke test for a deployed demo instance.

Usage: python -m scripts.smoke_demo https://your-demo.onrender.com
"""
import sys
import urllib.error
import urllib.request


def http_fetch(base, method, path, timeout=90):
    data = b"{}" if method == "POST" else None
    req = urllib.request.Request(
        base.rstrip("/") + path,
        method=method,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


# (name, method, path, allowed status codes)
CHECKS = [
    ("health answers 200", "GET", "/health", {200}),
    ("API docs are served", "GET", "/docs", {200}),
    ("stories readable (200, or 401 if API_KEY is set)", "GET", "/stories", {200, 401}),
    ("register is blocked in demo mode", "POST", "/auth/register", {403}),
    ("cleanup is blocked in demo mode", "POST", "/run-cleanup", {401, 403}),
]


def run_checks(fetch):
    results = []
    for name, method, path, allowed in CHECKS:
        try:
            status, _ = fetch(method, path)
            results.append((name, status in allowed, "status %s" % status))
        except Exception as exc:  # network error, timeout
            results.append((name, False, "error: %s" % exc))
    return results


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: python -m scripts.smoke_demo https://your-demo.onrender.com")
        return 2
    base = argv[0]
    results = run_checks(lambda m, p: http_fetch(base, m, p))
    failed = 0
    for name, ok, detail in results:
        print("[%s] %s (%s)" % ("OK" if ok else "FAIL", name, detail))
        failed += 0 if ok else 1
    print("All checks passed." if not failed else "%d check(s) failed." % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
