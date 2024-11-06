#!/usr/bin/env bash

test_out=samples/.test_out
test_dump=samples/.test_dump
orig_dump=samples/.orig_dump

for xib in samples/*.xib ; do
	echo "Testing $xib"

	python ibtool.py --compile "$test_out" "$xib"

	python ibtool.py --dump "${xib/xib/nib}" > "$orig_dump"
	python ibtool.py --dump "$test_out" > "$test_dump"

	sleep 1
	diff -u "$orig_dump" "$test_dump"
	if [[ $? == 0 ]] ; then
		sleep 1
		echo "ok"
	else
		sleep 1
		echo "failed"
	fi
	rm -f "$test_out" "$test_dump" "$orig_dump"
done

