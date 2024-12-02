from . import ibtool
from . import ibdump
from . import compare
import sys

if sys.argv[1] == "--compile":
    ibtool.main()

elif sys.argv[1] == "--compare":
    compare.main(sys.argv[2], sys.argv[3])

elif sys.argv[1] == "--dump":
    ibdump.ibdump(sys.argv[2])
