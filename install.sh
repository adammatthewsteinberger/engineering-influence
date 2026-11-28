#!/bin/sh
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Installs everything `ei book create` needs to write a book on this machine, then checks it.
#
#   curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh
#
# With options (the script is on standard input, so they go after `sh -s --`):
#
#   curl -fsSL .../install.sh | sh -s -- --dry-run
#
#   --dry-run             print every command and change nothing
#   --skip-model          do not install Ollama or pull the model (about 13 GB)
#   --skip-tex            do not install the TeX toolchain (several GB)
#   --skip-search         do not start the local web search (needs Docker)
#   --with-claude-skill   also put the Claude Code skill in ~/.claude/skills
#   --version REF         the tag, branch or commit to install (default: main)
#
# What it does, in order, saying each step before it runs:
#   1. uv, if it is missing (https://docs.astral.sh/uv/), then `ei` itself with the extras a book needs
#   2. Ollama and the free local model, gpt-oss:20b
#   3. the TeX tools the last stage calls to build the PDF and the EPUB
#   4. a local SearXNG for the research stage, when Docker is here
#   5. a starter author profile, which is never written over one that exists
#   6. `ei doctor --ready`, and the command that writes a book
#
# It asks nothing, because a piped script has no keyboard: every choice is a flag. A step that needs
# administrator rights runs `sudo`, which asks for the password itself. It supports macOS with Homebrew
# and Linux with apt-get; on anything else it stops and says what to do by hand. Run it twice and the
# second run changes nothing that is already in place.
set -eu

REPOSITORY="adammatthewsteinberger/engineering-influence"
MODEL="gpt-oss:20b"
CONTEXT=32768
VERSION="main"
DRY_RUN=no
SKIP_MODEL=no
SKIP_TEX=no
SKIP_SEARCH=no
WITH_SKILL=no

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=yes ;;
    --skip-model) SKIP_MODEL=yes ;;
    --skip-tex) SKIP_TEX=yes ;;
    --skip-search) SKIP_SEARCH=yes ;;
    --with-claude-skill) WITH_SKILL=yes ;;
    --version)
      [ "$#" -ge 2 ] || { echo "error: --version needs a tag, branch or commit" >&2; exit 2; }
      VERSION="$2"
      shift
      ;;
    *) echo "error: unknown option $1 (the options are listed at the top of this script)" >&2; exit 2 ;;
  esac
  shift
done

case "$VERSION" in
  *[!A-Za-z0-9._/-]* | "" | -*) echo "error: --version $VERSION is not a tag, branch or commit" >&2; exit 2 ;;
esac

RAW="https://raw.githubusercontent.com/$REPOSITORY/$VERSION"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/engineering-influence"
PROFILE="$CONFIG/author.toml"

say() { printf '\n==> %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Every command that changes this machine goes through here, so --dry-run shows exactly what would run.
run() {
  printf '    + %s\n' "$*"
  [ "$DRY_RUN" = yes ] || "$@"
}

# Another project's own installer: fetched whole first, so a failed download stops here and is never
# run as an empty or half-arrived script (plain sh has no pipefail to catch that in a pipe).
run_script_from() {
  printf '    + %s\n' "curl -fsSL $1 | sh"
  [ "$DRY_RUN" = no ] || return 0
  fetched="$(curl -fsSL "$1")" || { echo "error: could not download $1" >&2; exit 1; }
  printf '%s\n' "$fetched" | sh
}

# Administrator rights only when they are needed, and never silently: the command is printed first.
as_root() {
  if [ "$(id -u)" -eq 0 ]; then run "$@"; else run sudo "$@"; fi
}

SYSTEM="$(uname -s)"
case "$SYSTEM" in
  Darwin)
    if ! have brew; then
      echo "error: this needs Homebrew on macOS. Install it from https://brew.sh, then run this again." >&2
      exit 1
    fi
    ;;
  Linux)
    if ! have apt-get && { [ "$SKIP_TEX" = no ] || [ "$SKIP_MODEL" = no ]; }; then
      echo "error: this installs packages with apt-get, which is not here." >&2
      echo "       Install the tools by hand (docs/WORKER_IMAGE.md lists them), then run this again" >&2
      echo "       with --skip-tex --skip-model to install ei alone." >&2
      exit 1
    fi
    ;;
  *)
    echo "error: $SYSTEM is not supported by this script (macOS and Linux are)." >&2
    echo "       docs/GETTING_STARTED.md has the steps to follow by hand." >&2
    exit 1
    ;;
esac

say "engineering-influence: installing what a book needs ($VERSION)"
[ "$DRY_RUN" = no ] || note "dry run: every command is printed and nothing is changed"
[ "$SKIP_MODEL" = yes ] || note "the model is a download of about 13 GB"
[ "$SKIP_TEX" = yes ] || note "the TeX tools are a download of several GB"

say "1 of 6: ei, the command"
if ! have uv; then
  note "uv is missing; installing it from astral.sh"
  run_script_from https://astral.sh/uv/install.sh
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi
run uv tool install --force "engineering-influence[runtime,publishing,mcp] @ git+https://github.com/$REPOSITORY@$VERSION"
PATH="$HOME/.local/bin:$PATH"
export PATH

say "2 of 6: the free local model"
if [ "$SKIP_MODEL" = yes ]; then
  note "skipped (--skip-model). Later: ollama pull $MODEL"
else
  if ! have ollama; then
    if [ "$SYSTEM" = Darwin ]; then
      run brew install ollama
    else
      run_script_from https://ollama.com/install.sh
    fi
  fi
  if [ "$SYSTEM" = Darwin ]; then
    # A prompt is assembled to fit this many tokens, so the server must really offer them.
    run launchctl setenv OLLAMA_CONTEXT_LENGTH "$CONTEXT"
    if curl -fsS -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      # However it was started (Homebrew, or the Ollama app), a server that answers is left running.
      note "Ollama is already running. If the check below reports a small context, quit and reopen it."
    else
      run brew services start ollama
    fi
  else
    note "set the context for the Ollama service: sudo systemctl edit ollama, then add"
    note "  [Service]"
    note "  Environment=OLLAMA_CONTEXT_LENGTH=$CONTEXT"
    note "and restart it: sudo systemctl restart ollama. ei doctor --ready checks the result."
  fi
  if [ "$DRY_RUN" = no ]; then
    waited=0
    until curl -fsS -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do
      waited=$((waited + 1))
      [ "$waited" -lt 30 ] || { echo "error: Ollama did not answer at http://127.0.0.1:11434 within a minute" >&2; exit 1; }
      sleep 2
    done
  fi
  run ollama pull "$MODEL"
fi

say "3 of 6: the tools that build the PDF and the EPUB"
if [ "$SKIP_TEX" = yes ]; then
  note "skipped (--skip-tex). Chapters will still be written; the last stage, build, will fail."
elif [ "$SYSTEM" = Darwin ]; then
  have lualatex && have latexmk && have tex4ebook || run brew install --cask mactex-no-gui
  have pdftoppm || run brew install poppler
  have epubcheck || run brew install epubcheck
  PATH="/Library/TeX/texbin:$PATH"
  export PATH
else
  as_root apt-get update
  as_root apt-get install -y --no-install-recommends \
    latexmk texlive-luatex texlive-latex-recommended texlive-latex-extra texlive-pictures \
    texlive-fonts-recommended texlive-plain-generic texlive-extra-utils poppler-utils epubcheck tex-gyre \
    default-jre-headless zip tidy
fi

say "4 of 6: a local web search for the research stage"
if [ "$SKIP_SEARCH" = yes ]; then
  note "skipped (--skip-search). Set EI_SEARXNG_URL or BRAVE_SEARCH_API_KEY before a run."
elif ! have docker || ! docker compose version >/dev/null 2>&1; then
  note "Docker with compose is not here, so no search was started."
  note "Set EI_SEARXNG_URL (a SearXNG you run) or BRAVE_SEARCH_API_KEY before a run."
else
  run mkdir -p "$CONFIG/searxng"
  run curl -fsSL -o "$CONFIG/searxng/docker-compose.yml" "$RAW/examples/searxng/docker-compose.yml"
  run curl -fsSL -o "$CONFIG/searxng/settings.yml" "$RAW/examples/searxng/settings.yml"
  if [ "$DRY_RUN" = no ] && [ ! -f "$CONFIG/searxng/.env" ]; then
    # The secret is made here and kept in a file only this user can read; it is never printed.
    (umask 077 && printf 'SEARXNG_SECRET=%s\n' "$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')" > "$CONFIG/searxng/.env")
  fi
  note "+ write $CONFIG/searxng/.env (a generated secret, mode 600), unless it exists"
  run docker compose -f "$CONFIG/searxng/docker-compose.yml" --env-file "$CONFIG/searxng/.env" up -d --wait
fi

say "5 of 6: your author profile"
if [ -e "$PROFILE" ]; then
  note "$PROFILE is already there and was left as it is"
else
  note "+ write $PROFILE (a starter: change every value to your own)"
  if [ "$DRY_RUN" = no ]; then
    mkdir -p "$CONFIG"
    (umask 077 && cat > "$PROFILE" <<'PROFILE_END'
# Your author profile. Change every value. It is never sent to a model: the assemble stage writes it
# onto the title, copyright and about-the-author pages. The full list of keys, and the optional
# [pricing] table a strict release needs, is in docs/CONFIGURATION.md.
author = "Your Name"
publisher = "Your Imprint"
edition = "First Edition"
author_bio = "One or two sentences about you, as you want them printed in the book."
PROFILE_END
    )
  fi
fi

if [ "$WITH_SKILL" = yes ]; then
  say "the Claude Code skill"
  run mkdir -p "$HOME/.claude/skills/engineering-influence"
  run curl -fsSL -o "$HOME/.claude/skills/engineering-influence/SKILL.md" \
    "$RAW/examples/claude-code/engineering-influence/SKILL.md"
fi

say "6 of 6: is this machine ready to make a book?"
status=0
if [ "$DRY_RUN" = yes ]; then
  note "+ EI_AUTHOR_PROFILE=$PROFILE ei doctor --ready"
else
  EI_AUTHOR_PROFILE="$PROFILE" ei doctor --ready || status=$?
fi

say "next"
note "1. Put your own details in $PROFILE"
note "2. Write a book:"
note "     ei book create --kind nonfiction \"your idea\" --budget-usd 5 --out ./my-book --profile $PROFILE"
note "   The local model is free; the budget is a cap that a paid model would count against."
[ "$status" -eq 0 ] || note "Some checks above failed. Each line says what to do; then run: ei doctor --ready"
exit "$status"
