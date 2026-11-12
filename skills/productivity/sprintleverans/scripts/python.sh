#!/usr/bin/env bash
# Prepare the locked runtime before starting any delivery command or test.
set -euo pipefail
skill_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' 'Sprintleverans needs uv on PATH. Install uv, then rerun this launcher; no command was started.' >&2
  exit 1
fi
if ! uv sync --project "$skill_dir" --locked --managed-python --python 3.12 --no-dev; then
  printf '%s\n' 'Sprintleverans runtime is not ready; no command was started. Restore network access for the first bootstrap (unset UV_OFFLINE if set), or restore a populated uv cache, then rerun this launcher.' >&2
  exit 1
fi
exec uv run --project "$skill_dir" --no-sync --managed-python --python 3.12 --no-env-file python -I "$@"
