from . import ibdump
from . import ibtool
from . import compare
from . import xibmap as xibmap_mod
import sys
import argparse

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
    args = parser.parse_args()

    if args.xibmap:
        xibmap_mod.print_xibmap(args.input)

    elif args.compile:
        ibtool.ib_compile(args.input, args.compile)

    elif args.compare:
        compare.main(args.compare, args.input, xib_path=args.xib)

    elif args.dump:
        ibdump.ibdump(args.input, args.encoding, args.tree, args.sort, args.filter)

    else:
        parser.print_help()
        sys.exit()

if __name__ == "__main__":
    run()
