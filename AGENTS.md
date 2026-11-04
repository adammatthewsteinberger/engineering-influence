# Contribution guidance

Keep domain code pure. Put external effects behind ports and adapters. Every
pipeline side effect must be bounded, idempotent, observable, and recoverable.
Run the local checks described in `CONTRIBUTING.md` before opening a PR.
