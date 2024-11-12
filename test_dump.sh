#!/usr/bin/env bash

set -euo pipefail

test_out=$(mktemp)

xib="$1"

python ibtool.py --compile "$test_out" "$xib"
python ibtool.py --dump "$test_out"
rm -f "$test_out"
