from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSlider", elem, parent)

    parse_children(ctx, elem, obj)
    
    cell_elem = elem.find("sliderCell")
    continuous = cell_elem is not None and cell_elem.attrib.get("continuous", "NO") == "YES"

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSEnabled", attrib="enabled", default="YES", map=MAP_YES_NO, skip_default=False),
        PropSchema(prop="NSSubviews", const=NibMutableList()),
        PropSchema(prop="NSSuperview", const=obj.xib_parent()),
        PropSchema(prop="NSControlSendActionMask", const=70 if continuous else 4),
        PropSchema(prop="NSControlUsesSingleLineMode", const=False),
        PropSchema(prop="NSAllowsLogicalLayoutDirection", const=False),
    ])

    h = obj.extraContext.get("horizontalHuggingPriority", "250")
    v = obj.extraContext.get("verticalHuggingPriority", "750")
    if h != "250" or v != "750":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    if identifier := elem.attrib.get("identifier"):
        obj["NSReuseIdentifierKey"] = NibString.intern(identifier)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
