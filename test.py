#!/usr/bin/env python3

import glob
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor


def _read_extra_args(xib):
    args_file = os.path.splitext(xib)[0] + ".args"
    if os.path.isfile(args_file):
        with open(args_file) as f:
            return shlex.split(f.read())
    return []


def run_test(xib):
    if xib.endswith(".storyboard"):
        return run_storyboard_test(xib)

    extra_args = _read_extra_args(xib)

    with tempfile.NamedTemporaryFile(suffix=".nib", delete=False) as f:
        test_out = f.name

    try:
        compile_result = subprocess.run(
            [sys.executable, "-m", "ibtool", "--compile", test_out, xib] + extra_args,
            capture_output=True,
            text=True,
        )

        if not os.path.isfile(test_out) or os.path.getsize(test_out) == 0:
            output = (compile_result.stdout + compile_result.stderr).strip()
            return False, xib, output

        nib = xib.removesuffix(".xib") + ".nib"
        compare_result = subprocess.run(
            [sys.executable, "-m", "ibtool", "--compare", nib, test_out],
            capture_output=True,
            text=True,
        )

        if compare_result.returncode == 0:
            return True, xib, ""
        else:
            output = (compare_result.stdout + compare_result.stderr).strip()
            return False, xib, output
    finally:
        if os.path.exists(test_out):
            os.unlink(test_out)


def run_storyboard_test(sb):
    extra_args = _read_extra_args(sb)
    test_out = tempfile.mkdtemp(suffix=".storyboardc")

    try:
        compile_result = subprocess.run(
            [sys.executable, "-m", "ibtool", "--compile", test_out, sb] + extra_args,
            capture_output=True,
            text=True,
        )

        if compile_result.returncode != 0:
            output = (compile_result.stdout + compile_result.stderr).strip()
            return False, sb, output

        ref_dir = sb.removesuffix(".storyboard") + ".out"
        if not os.path.isdir(ref_dir):
            return False, sb, f"Reference directory not found: {ref_dir}"

        compare_result = subprocess.run(
            [sys.executable, "-m", "ibtool", "--compare", ref_dir, test_out],
            capture_output=True,
            text=True,
        )

        if compare_result.returncode == 0:
            return True, sb, ""
        else:
            output = (compare_result.stdout + compare_result.stderr).strip()
            return False, sb, output
    finally:
        if os.path.exists(test_out):
            shutil.rmtree(test_out)


def main():
    if len(sys.argv) > 1:
        xibs = sys.argv[1:]
    else:
        xibs = sorted(glob.glob("samples/correct/*.xib") + glob.glob("samples/correct/*.storyboard") + glob.glob("samples/correct/Base.lproj/*.storyboard"))

    workers = int(os.environ.get("IBTOOL_TEST_WORKERS", 8))

    passed = 0
    failed = 0

    with ProcessPoolExecutor(max_workers=workers) as pool:
        for success, xib, output in pool.map(run_test, xibs):
            if success:
                passed += 1
            else:
                failed += 1
                print(f"FAIL: {xib}")
                if output:
                    print(output)
                print()

    print(f"Passed: {passed}  Failed: {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
