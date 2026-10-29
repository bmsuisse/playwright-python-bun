#!/usr/bin/env bash
# Open an issue for a failed workflow run unless one with the same title is open.
# Usage: report_failure.sh <title> <run-url>; needs GH_TOKEN.
set -euo pipefail
title="$1"
run_url="$2"
if [ -n "$(gh issue list --state open --search "\"$title\" in:title" --json number --jq '.[].number')" ]; then
  echo "An issue for \"$title\" is already open."
  exit 0
fi
gh issue create --title "$title" --body "See $run_url. Fix it locally (FORK.md, \"When the sync fails\") and re-run the workflow."
