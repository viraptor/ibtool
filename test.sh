#!/usr/bin/env bash

test_out=$(mktemp)

if [[ $# -gt 0 ]] ; then
	xibs_to_test="$@"
else
	xibs_to_test=samples/correct/*.xib
fi

passed=0
failed=0

for xib in $xibs_to_test ; do
	compile_output=$(python3 -m ibtool --compile "$test_out" "$xib" 2>&1)

	if [ -r "$test_out" ] ; then
		output=$(python3 -m ibtool --compare "${xib/xib/nib}" "$test_out" 2>&1)
		if [[ $? == 0 ]] ; then
			passed=$((passed + 1))
		else
			failed=$((failed + 1))
			echo "FAIL: $xib"
			echo "$output"
			echo
		fi
		rm -f "$test_out"
	else
		failed=$((failed + 1))
		echo "FAIL: $xib"
		echo "$compile_output"
		echo
	fi
done

echo "Passed: $passed  Failed: $failed"
