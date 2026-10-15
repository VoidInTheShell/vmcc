#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
exec python3 "$(dirname -- "$0")/build-boot-disk.py" "$@"
