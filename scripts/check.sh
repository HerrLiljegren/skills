#!/usr/bin/env bash
# Run tracked regression suites and syntax checks from any working directory.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$repo_dir"
for tool in git bash uv node jq iconv; do
  command -v "$tool" >/dev/null 2>&1 || { printf 'Required tool missing: %s\n' "$tool" >&2; exit 1; }
done
runtime="$repo_dir/skills/productivity/sprintleverans/scripts/python.sh"
while IFS= read -r -d '' file; do
  printf 'Shell syntax: %s\n' "$file"
  bash -n "$file"
done < <(git ls-files -z -- '*.sh')
# unittest discovery needs an explicit start directory for these non-package scripts.
while IFS= read -r directory; do
  printf 'Python tests: %s\n' "$directory"
  bash "$runtime" -m unittest discover -s "$directory" -p 'test_*.py' -v
done < <(git ls-files -- '**/test_*.py' | while IFS= read -r file; do dirname -- "$file"; done | LC_ALL=C sort -u)
while IFS= read -r -d '' file; do
  printf 'Node tests: %s (regular and linked checkout)\n' "$file"
  node --check "$file"
  node "$file"
  LAUNCH_TEST_LINKED=1 node "$file"
done < <(git ls-files -z -- '**/tests/*.mjs')
