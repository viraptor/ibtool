from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSProgressIndicator", elem, parent)

    bezeled_value = elem.attrib.get("bezeled", "YES") == "YES"
    bezeled = 0x1 if bezeled_value else 0
    indeterminate_value = elem.attrib.get("indeterminate", "NO") == "YES"
    indeterminate = 0x2 if indeterminate_value else 0
    style_value = elem.attrib.get("style", "bar")
    style = {"bar": 0, "spinning": 0x1000}[style_value]

    _xibparser_common_view_attributes(ctx, elem, parent, obj)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    if elem.attrib.get("maxValue"):
        obj["NSMaxValue"] = float(elem.attrib["maxValue"])
    if elem.attrib.get("minValue"):
        obj["NSMinValue"] = float(elem.attrib["minValue"])
    obj.flagsOr("NSpiFlags", 0x4004 | bezeled | indeterminate | style)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
