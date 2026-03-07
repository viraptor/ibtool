#!/usr/bin/env bash

test_out=$(mktemp)

if [[ $# -gt 0 ]] ; then
	xibs_to_test="$@"
else
	xibs_to_test=samples/correct/*.xib
fi

for xib in $xibs_to_test ; do
	echo "Testing $xib"

	python3 -m ibtool --compile "$test_out" "$xib"

	python3 -m ibtool --compare "${xib/xib/nib}" "$test_out"
	if [[ $? == 0 ]] ; then
		echo "ok"
	else
		echo "failed"
	fi
	rm -f "$test_out"
done

