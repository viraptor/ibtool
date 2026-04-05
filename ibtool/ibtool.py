#!/usr/bin/python

import sys
import os
import xml.etree.ElementTree as ET

from . import genlib
from . import ibdump
from . import xibparser


def ib_compile(inpath, outpath, module=None):
    suffix = None
    if inpath.endswith(".xib"):
        suffix = "xib"
    elif inpath.endswith(".storyboard"):
        suffix = "storyboard"

    if suffix is None:
        sys.exit("ib_compile: Only .xib and .storyboard files are currently supported.")

    if suffix == "xib":
        ib_compile_xib(inpath, outpath, module=module)
    elif suffix == "storyboard":
        ib_compile_storyboard(inpath, outpath, module=module)


def ib_compile_xib(inpath, outpath, module=None):
    tree = ET.parse(inpath)
    root = tree.getroot()
    context, nibroot = xibparser.ParseXIBObjects(root, module=module)
    outbytes = genlib.CompileNibObjects([nibroot])

    if context.deployment:
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        nibpath = os.path.join(outpath, "keyedobjects-101300.nib")
    else:
        nibpath = outpath
    with open(nibpath, "wb") as fl:
        fl.write(outbytes)


def ib_compile_storyboard(inpath, outpath, module=None):
    tree = ET.parse(inpath)
    xibparser.CompileStoryboard(tree, outpath, module=module)
