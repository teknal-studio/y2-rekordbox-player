"""Shared test setup: put tools/ and build/ on the import path."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("tools", "build"):
    path = os.path.join(ROOT, sub)
    if path not in sys.path:
        sys.path.insert(0, path)
