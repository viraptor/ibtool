#!/usr/bin/env zsh

for xib in samples/*.xib ; do
	echo "Testing $xib"
	python ibtool.py --compile samples/output_test.nib "$xib"
	if diff --side-by-side <(python ibtool.py --dump "${xib/\.xib/.nib}") <(python ibtool.py --dump samples/output_test.nib) ; then
		echo "ok"
	else
		echo "failed"
	fi
done
