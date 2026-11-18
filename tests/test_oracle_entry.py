import importlib
import pathlib
import re

SRC = (pathlib.Path(__file__).resolve().parent.parent / "dashboard" / "oracle_app.py").read_text(
    encoding="utf-8"
)


def test_every_page_function_exists():
    pairs = set(re.findall(r"\b(feed|misc|overview|report|research)\.(\w+)\b", SRC))
    assert pairs
    for module, name in pairs:
        mod = importlib.import_module(f"dashboard.oracle.{module}")
        assert callable(getattr(mod, name, None)), f"{module}.{name} is missing"