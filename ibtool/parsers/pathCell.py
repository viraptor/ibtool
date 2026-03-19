from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibList, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import __xibparser_cell_flags, __xibparser_cell_options, makeSystemColor
from ..parsers_base import parse_children


def _make_path_component_cells(url_string, font_obj, bg_color, text_color):
    if not url_string or not url_string.startswith("file:///"):
        return NibMutableList([])

    path = url_string[len("file://"):]
    parts = [p for p in path.split("/") if p]

    cells = []
    current_url = "file:///"
    volume_cell = NibObject("NSPathComponentCell")
    volume_cell["NSCellFlags"] = 0x4000040
    volume_cell["NSCellFlags2"] = 0x10000400
    volume_cell["NSContents"] = NibString.intern("Macintosh HD")
    if font_obj:
        volume_cell["NSSupport"] = font_obj
    if bg_color:
        volume_cell["NSBackgroundColor"] = bg_color
    if text_color:
        volume_cell["NSTextColor"] = text_color
    url_obj = NibObject("NSURL")
    url_obj["NS.base"] = NibNil()
    url_obj["NS.relative"] = NibString.intern("file:///")
    volume_cell["NSURL"] = url_obj
    cells.append(volume_cell)

    for part in parts:
        current_url += part
        cell = NibObject("NSPathComponentCell")
        cell["NSCellFlags"] = 0x4000040
        cell["NSCellFlags2"] = 0x10000400
        cell["NSContents"] = NibString.intern(part)
        if font_obj:
            cell["NSSupport"] = font_obj
        if bg_color:
            cell["NSBackgroundColor"] = bg_color
        if text_color:
            cell["NSTextColor"] = text_color
        url_obj = NibObject("NSURL")
        url_obj["NS.base"] = NibNil()
        url_obj["NS.relative"] = NibString.intern(current_url)
        cell["NSURL"] = url_obj
        cells.append(cell)
        current_url += "/"

    return NibMutableList(cells)


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSPathCell", elem, parent)
    ctx.extraNibObjects.append(obj)

    key = elem.attrib.get("key")
    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)
        obj["NSSupport"] = NibNil()
        obj["NSControlView"] = obj.xib_parent()

        parse_children(ctx, elem, obj)

        url_string = obj.extraContext.get("url_string")
        if url_string:
            url_obj = NibObject("NSURL")
            url_obj["NS.base"] = NibNil()
            url_obj["NS.relative"] = NibString.intern(url_string)
            obj["NSContents"] = url_obj
        else:
            obj.setIfEmpty("NSContents", NibString.intern(""))

        font_obj = obj.get("NSSupport")
        bg_color = makeSystemColor("textBackgroundColor")
        text_color = obj.get("NSTextColor") or makeSystemColor("controlTextColor")
        obj["NSPathComponentCells"] = _make_path_component_cells(
            url_string, font_obj, bg_color, text_color)

        obj["NSDelegate"] = obj.xib_parent()

        allowed_types = obj.extraContext.get("allowedTypes", [])
        obj["NSAllowedTypes"] = NibList(allowed_types)

        parent["NSCell"] = obj

    return obj
