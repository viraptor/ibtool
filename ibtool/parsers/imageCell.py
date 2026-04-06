from ..models import ArchiveContext, NibObject, XibObject, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import __xibparser_cell_options, __xibparser_cell_flags, make_image, make_inline_image
from ..parsers_base import parse_children
from ..constants import CellFlags

IMAGECELL_CELLFLAGS_THRESHOLD = 2494

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
        if ctx.toolsVersion <= IMAGECELL_CELLFLAGS_THRESHOLD:
            obj.flagsOr("NSCellFlags", CellFlags.TYPE_IMAGE_CELL)

        alignment_value = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
        obj["NSAlign"] = alignment_value
        obj["NSAnimates"] = elem.attrib.get("animates", "NO") == "YES"
        if image_name := elem.attrib.get("image"):
            obj["NSContents"] = make_image(image_name, obj, ctx)
        obj["NSControlView"] = parent
        obj["NSImageAnimation"] = -1
        obj["NSScale"] = {
            "proportionallyDown": 0,
            "axesIndependently": 1,
            "none": 2,
            "proportionallyUpOrDown": 3,
        }[elem.attrib.get("imageScaling", "none")]
        obj["NSStyle"] = {
            None: 0, "none": 0, "photo": 1, "grayBezel": 2, "groove": 3, "button": 4,
        }.get(elem.attrib.get("imageFrameStyle"), 0)
        parent["NSCell"] = obj

    elif key == "dataCell":
        __xibparser_cell_flags(elem, obj, parent)
        if obj.get("NSSupport") is not None:
            obj.flagsOr("NSCellFlags", CellFlags.TYPE_TEXT_CELL)

        image_alignment = elem.attrib.get("imageAlignment")
        IMAGE_ALIGNMENT_MAP = {
            None: 0, "center": 0, "top": 1, "topLeft": 2, "topRight": 3,
            "left": 4, "bottom": 5, "bottomLeft": 6, "bottomRight": 7, "right": 8,
        }
        obj["NSAlign"] = IMAGE_ALIGNMENT_MAP.get(image_alignment, 0)
        obj["NSAnimates"] = elem.attrib.get("animates", "NO") == "YES"
        if image_name := elem.attrib.get("image"):
            obj["NSContents"] = make_inline_image(image_name, obj, ctx)
        table_view = parent.get("NSTableView") if parent.originalclassname() == "NSTableColumn" else parent
        obj["NSControlView"] = table_view
        obj["NSImageAnimation"] = -1
        obj["NSScale"] = {
            "proportionallyDown": 0,
            "axesIndependently": 1,
            "none": 2,
            "proportionallyUpOrDown": 3,
        }[elem.attrib.get("imageScaling", "none")]
        obj["NSStyle"] = {
            None: 0, "none": 0, "photo": 1, "grayBezel": 2, "groove": 3, "button": 4,
        }.get(elem.attrib.get("imageFrameStyle"), 0)
        parent["NSDataCell"] = obj

    else:
        raise Exception(f"Unknown key for imageCell: {key}")
        

    return obj

