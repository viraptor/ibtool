#!/usr/bin/env bash

test_out=$(mktemp)

xibs_to_test="samples/minimal.xib samples/blocklist.xib samples/windows.xib samples/window.xib samples/with_view.xib"

for xib in $xibs_to_test ; do
	echo "Testing $xib"

	python ibtool.py --compile "$test_out" "$xib"

	python compare.py "${xib/xib/nib}" "$test_out"
	if [[ $? == 0 ]] ; then
		echo "ok"
	else
		echo "failed"
	fi
	rm -f "$test_out"
done

