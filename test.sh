#!/usr/bin/env bash

test_out=$(mktemp)

if [[ $# -gt 0 ]] ; then
	xibs_to_test="$@"
else
	xibs_to_test="
		samples/minimal.xib
		samples/blocklist.xib
		samples/windows.xib
		samples/window.xib
		samples/with_view.xib
		samples/with_app_class.xib
		samples/blocklist_big.xib
		samples/test1.xib
		samples/test2.xib
		samples/test3.xib
		samples/test4.xib
		samples/test5_connect.xib
		samples/test8_menu.xib
		samples/test9_menu_conn.xib
		samples/test11_text_view_back.xib
		samples/test12_text_view_border.xib
		samples/test13_clip_flags.xib
		samples/test14_custom_classes.xib
		samples/test15_custom_classes.xib
		samples/test18_autoresize.xib
		samples/test19_2_layouts.xib
		samples/test21_masktranslate.xib
		"
fi

for xib in $xibs_to_test ; do
	echo "Testing $xib"

	python -m ibtool --compile "$test_out" "$xib"

	python -m ibtool --compare "${xib/xib/nib}" "$test_out"
	if [[ $? == 0 ]] ; then
		echo "ok"
	else
		echo "failed"
	fi
	rm -f "$test_out"
done

