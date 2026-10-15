#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"
test -z "$(git status --porcelain --untracked-files=normal)"
mkdir -p dist
git archive --format=tar.gz --prefix=vmcc/ --output=dist/vmcc-source.tar.gz HEAD
(cd dist && sha256sum vmcc-source.tar.gz > SHA256SUMS)
printf 'Source archive created from commit %s\n' "$(git rev-parse HEAD)"
