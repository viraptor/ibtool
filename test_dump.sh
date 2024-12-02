#!/usr/bin/env bash

set -euo pipefail

test_out=$(mktemp)

xib="$1"

python -m ibtool --compile "$test_out" "$xib"
python -m ibtool --dump "$test_out"
rm -f "$test_out"
