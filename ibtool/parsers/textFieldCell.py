from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from .helpers import __xibparser_cell_flags, __xibparser_cell_options
from ..parsers_base import parse_children
from ..constants import CONTROL_SIZE_MAP2

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSTextFieldCell", elem, parent)
    ctx.extraNibObjects.append(obj)

    key = elem.attrib.get("key")
    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)

        obj["NSContents"] = elem.attrib.get("title", NibString.intern(''))
        obj["NSSupport"] = NibNil() # TODO
        obj["NSControlView"] = obj.xib_parent()
        if placeholder := elem.attrib.get("placeholderString"):
            obj["NSPlaceholderString"] = NibString.intern(placeholder)
        if ctx.toolsVersion < 23504:
            obj["NSCharacterPickerEnabled"] = True
        if elem.attrib.get("drawsBackground") == "YES":
            obj["NSDrawsBackground"] = True
        parse_children(ctx, elem, obj)

        parent["NSCell"] = obj

    elif key == "dataCell":
        parse_children(ctx, elem, obj)
        __xibparser_cell_flags(elem, obj, parent)
        obj["NSContents"] = NibString.intern(elem.attrib.get("title", ""))
        obj["NSControlSize2"] = CONTROL_SIZE_MAP2[elem.attrib.get("controlSize")]

        obj["NSControlView"] = obj.xib_parent().xib_parent() # should be table not the column
        assert obj["NSControlView"].originalclassname() == "NSTableView"

        parent["NSDataCell"] = obj

    else:
        raise Exception(f"unknown key {key}")

    return obj
