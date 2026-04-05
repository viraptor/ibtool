from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableList, NibData, NibList, NibInlineString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import __xibparser_cell_options, __xibparser_cell_flags, make_image
from ..parsers_base import parse_children
from ..constants import CellFlags

IMAGECELL_CELLFLAGS_THRESHOLD = 2494

def _make_inline_image(name: str, parent: NibObject, ctx: "ArchiveContext") -> NibObject:
    res = ctx.imageResources.get(name)
    tiff_data = ctx.imageData.get(name)
    if res is None or name.startswith("NS") or tiff_data is None:
        return make_image(name, parent, ctx)
    plist_info = ctx.imagePlistData.get(name, {})
    tiff_reps = plist_info.get("tiff_reps", [tiff_data])
    plist_objects = plist_info.get("plist_objects", [])

    # Extract image flags and size from plist root object
    image_flags = 0x20c00000
    image_size = f"{{{res[0]}, {res[1]}}}"
    if len(plist_objects) > 1 and isinstance(plist_objects[1], dict):
        root_obj = plist_objects[1]
        if "NSImageFlags" in root_obj:
            image_flags = root_obj["NSImageFlags"]
        ns_size_uid = root_obj.get("NSSize")
        if ns_size_uid is not None and hasattr(ns_size_uid, 'data'):
            size_str = plist_objects[ns_size_uid.data]
            if isinstance(size_str, str):
                image_size = size_str

    obj = NibObject("NSImage", parent)
    obj["NSImageFlags"] = image_flags
    obj["NSSize"] = NibString.intern(image_size)

    rep_arrays = []
    for tiff in tiff_reps:
        bitmap_rep = NibObject("NSBitmapImageRep", obj)
        bitmap_rep["NSTIFFRepresentation"] = NibData(tiff)
        bitmap_rep["NSInternalLayoutDirection"] = 0
        num_zero = NibObject("NSNumber", obj)
        num_zero["NS.intval"] = 0
        rep_arrays.append(NibList([num_zero, bitmap_rep]))
    obj["NSReps"] = NibMutableList(rep_arrays)

    # Build color - check plist for extended color info
    color = NibObject("NSColor", obj)
    color["NSColorSpace"] = 3
    color["NSWhite"] = NibInlineString(b"0 0\x00")
    _apply_plist_color(color, obj, plist_objects)
    obj["NSColor"] = color
    obj["NSResizingMode"] = 0
    obj["NSTintColor"] = NibNil()
    return obj

def _apply_plist_color(color: NibObject, parent: NibObject, plist_objects: list) -> None:
    """Apply extended color info from the plist if available."""
    for o in plist_objects:
        if isinstance(o, dict) and "NSComponents" in o and "NSCustomColorSpace" in o:
            if isinstance(o.get("NSComponents"), bytes):
                color["NSComponents"] = NibInlineString(o["NSComponents"])
            cs_uid = o.get("NSCustomColorSpace")
            if cs_uid is not None and hasattr(cs_uid, 'data'):
                cs_obj = plist_objects[cs_uid.data]
                if isinstance(cs_obj, dict):
                    cs = NibObject("NSColorSpace", parent)
                    if "NSID" in cs_obj:
                        cs["NSID"] = cs_obj["NSID"]
                    if "NSModel" in cs_obj:
                        cs["NSModel"] = cs_obj["NSModel"]
                    icc_uid = cs_obj.get("NSICC")
                    if icc_uid is not None and hasattr(icc_uid, 'data'):
                        icc_data = plist_objects[icc_uid.data]
                        if isinstance(icc_data, bytes):
                            cs["NSICC"] = NibData(icc_data)
                    color["NSCustomColorSpace"] = cs
            if "NSWhite" in o and isinstance(o["NSWhite"], bytes):
                white_val = o["NSWhite"]
                if white_val.startswith(b"0"):
                    color["NSLinearExposure"] = NibInlineString(b"1")
            break

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
            obj["NSContents"] = _make_inline_image(image_name, obj, ctx)
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

