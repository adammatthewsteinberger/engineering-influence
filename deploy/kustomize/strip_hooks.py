"""Reads a Helm render on stdin and writes it for Kustomize: no Helm hook annotations, and a stable Job name."""

import re
import sys

text = sys.stdin.read()
text = re.sub(r'\n\s*"helm\.sh/hook[^\n]*', "", text)
text = re.sub(r"(name: [^\n]*-migrate)-\d+", r"\1", text)
sys.stdout.write(text)
