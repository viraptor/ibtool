from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableList, NibData, NibList, NibInlineString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import __xibparser_cell_options, __xibparser_cell_flags, make_image
from ..parsers_base import parse_children

def _make_inline_image(name: str, parent: NibObject, ctx: "ArchiveContext") -> NibObject:
    res = ctx.imageResources.get(name)
    tiff_data = ctx.imageData.get(name)
    if res is None or name.startswith("NS") or tiff_data is None:
        return make_image(name, parent, ctx)
    obj = NibObject("NSImage", parent)
    obj["NSImageFlags"] = 0x20c00000
    obj["NSSize"] = NibString.intern(f"{{{res[0]}, {res[1]}}}")
    bitmap_rep = NibObject("NSBitmapImageRep", obj)
    bitmap_rep["NSTIFFRepresentation"] = NibData(tiff_data)
    bitmap_rep["NSInternalLayoutDirection"] = 0
    num_zero = NibObject("NSNumber", obj)
    num_zero["NS.intval"] = 0
    rep_array = NibList([num_zero, bitmap_rep])
    reps = NibMutableList([rep_array])
    obj["NSReps"] = reps
    color = NibObject("NSColor", obj)
    color["NSColorSpace"] = 3
    color["NSWhite"] = NibInlineString(b"0 0\x00")
    obj["NSColor"] = color
    obj["NSResizingMode"] = 0
    obj["NSTintColor"] = NibNil()
    return obj

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None
    assert parent.originalclassname() in ("NSImageView", "NSTableColumn"), parent.originalclassname()

    key = elem.attrib["key"]

    obj = XibObject(ctx, "NSImageCell", elem, parent)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    parse_children(ctx, elem, obj)

    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)

        alignment_value = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
        obj["NSAlign"] = alignment_value
        obj["NSAnimates"] = elem.attrib.get("animates", "NO") == "YES"
        obj["NSContents"] = NibNil()
        obj["NSControlView"] = parent
        obj["NSImageAnimation"] = -1
        obj["NSScale"] = {
            "proportionallyDown": 0,
            "axesIndependently": 1,
            "none": 2,
            "proportionallyUpOrDown": 3,
        }[elem.attrib.get("imageScaling", "none")]
        obj["NSStyle"] = 0
        if image_name := elem.attrib.get("image"):
            obj["NSContents"] = make_image(image_name, obj, ctx)
        parent["NSCell"] = obj

    elif key == "dataCell":
        __xibparser_cell_flags(elem, obj, parent)

        alignment_value = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
        obj["NSAlign"] = alignment_value
        obj["NSAnimates"] = elem.attrib.get("animates", "NO") == "YES"
        obj["NSContents"] = NibNil()
        table_view = parent.get("NSTableView") if parent.originalclassname() == "NSTableColumn" else parent
        obj["NSControlView"] = table_view
        obj["NSImageAnimation"] = -1
        obj["NSScale"] = {
            "proportionallyDown": 0,
            "axesIndependently": 1,
            "none": 2,
            "proportionallyUpOrDown": 3,
        }[elem.attrib.get("imageScaling", "none")]
        obj["NSStyle"] = 0
        if image_name := elem.attrib.get("image"):
            obj["NSContents"] = _make_inline_image(image_name, obj, ctx)
        parent["NSDataCell"] = obj

    else:
        raise Exception(f"Unknown key for imageCell: {key}")
        

    return obj

