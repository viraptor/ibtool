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
    parser.add_argument("input")
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
    args = parser.parse_args()

    if args.xibmap:
        xibmap_mod.print_xibmap(args.input)

    elif args.compile:
        ibtool.ib_compile(args.input, args.compile, module=args.module)
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
