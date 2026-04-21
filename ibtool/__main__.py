from . import ibdump
from . import ibtool
from . import compare
from . import xibmap as xibmap_mod
import sys
import argparse
import plistlib


def _output_diagnostics(args):
    result = {}
    if args.errors:
        result["com.apple.ibtool.document.errors"] = {}
    if args.notices:
        result["com.apple.ibtool.document.notices"] = {}
    if args.warnings:
        result["com.apple.ibtool.document.warnings"] = {}
    if not result:
        return
    fmt = args.output_format or "xml1"
    if fmt == "human-readable-text":
        return
    if fmt == "binary1":
        sys.stdout.buffer.write(plistlib.dumps(result, fmt=plistlib.FMT_BINARY))
    else:
        sys.stdout.buffer.write(plistlib.dumps(result, fmt=plistlib.FMT_XML))


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='?')
    parser.add_argument("--compile", metavar="output")
    parser.add_argument("--compare", metavar="input2")
    parser.add_argument("--xib", metavar="XIB", help="XIB source file for annotating --compare output with XIB element ids")
    parser.add_argument("--xibmap", action="store_true", help="Show mapping from XIB element ids to NIB object indices (input must be a .xib)")
    parser.add_argument("--dump", action="store_true")
    parser.add_argument("-e", "--encoding", action="store_true", help="Show encoding")
    parser.add_argument("-t", "--tree", action="store_true", help="Show tree")
    parser.add_argument("-s", "--sort", action="store_true", help="Sort keys")
    parser.add_argument("-f", "--filter", metavar="PATH", help="Structure path to dump, segments separated by / (e.g. NSView/NSSubviews/1/NSButton)")
    parser.add_argument("--errors", action="store_true", help="Include document error messages in plist output")
    parser.add_argument("--warnings", action="store_true", help="Include document warning messages in plist output")
    parser.add_argument("--notices", action="store_true", help="Include document notice messages in plist output")
    parser.add_argument("--output-format", choices=["xml1", "binary1", "human-readable-text"],
                        help="Output format for diagnostics (default: xml1)")
    parser.add_argument("--module", metavar="MODULE",
                        help="Target module name for Swift class name mangling")
    parser.add_argument("--output-partial-info-plist", metavar="PATH",
                        help="Write a partial Info.plist with build-time metadata to PATH")
    parser.add_argument("--auto-activate-custom-fonts", action="store_true",
                        help="Emit bundled-font metadata into the partial Info.plist (no effect on NIB contents)")
    parser.add_argument("--target-device", metavar="DEVICE",
                        help="Target device; only 'mac' is supported")
    parser.add_argument("--minimum-deployment-target", metavar="VERSION",
                        help="Minimum deployment target (accepted but ignored)")
    parser.add_argument("--version", action="store_true", help="Version")
    args = parser.parse_args()
    
    if args.version:
        print('<?xml version="1.0" encoding="UTF-8"?>')
        print('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">')
        print('<plist version="1.0">')
        print('<dict>')
        print('        <key>com.apple.ibtool.version</key>')
        print('        <dict>')
        print('                <key>bundle-version</key>')
        print('                <string>24765</string>')
        print('                <key>short-bundle-version</key>')
        print('                <string>26.4.1</string>')
        print('        </dict>')
        print('</dict>')
        print('</plist>')
        sys.exit()

    if args.target_device is not None and args.target_device != "mac":
        print(f"unsupported target device: {args.target_device!r} (only 'mac' is supported)")
        sys.exit(1)

    if not args.input:
        print('input file required')
        sys.exit(1)

    if args.xibmap:
        xibmap_mod.print_xibmap(args.input)

    elif args.compile:
        ibtool.ib_compile(args.input, args.compile, module=args.module)
        if args.output_partial_info_plist:
            with open(args.output_partial_info_plist, "wb") as f:
                f.write(plistlib.dumps({}, fmt=plistlib.FMT_XML))
        _output_diagnostics(args)

    elif args.compare:
        compare.main(args.compare, args.input, xib_path=args.xib)

    elif args.dump:
        ibdump.ibdump(args.input, args.encoding, args.tree, args.sort, args.filter)

    elif args.errors or args.warnings or args.notices:
        _output_diagnostics(args)

    else:
        parser.print_help()
        sys.exit()

if __name__ == "__main__":
    run()
