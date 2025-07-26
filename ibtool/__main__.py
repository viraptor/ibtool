from . import ibdump
from . import ibtool
from . import compare
import sys
import argparse

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--compile", metavar="output")
    parser.add_argument("--compare", metavar="input2")
    parser.add_argument("--dump", action="store_true")
    parser.add_argument("-e", "--encoding", action="store_true", help="Show encoding")
    parser.add_argument("-t", "--tree", action="store_true", help="Show tree")
    parser.add_argument("-s", "--sort", action="store_true", help="Sort keys")
    args = parser.parse_args()

    if args.compile:
        ibtool.ib_compile(args.input, args.compile)

    elif args.compare:
        compare.main(args.compare, args.input)

    elif args.dump:
        ibdump.ibdump(args.input, args.encoding, args.tree, args.sort)

    else:
        parser.print_help()
        sys.exit()

if __name__ == "__main__":
    run()
