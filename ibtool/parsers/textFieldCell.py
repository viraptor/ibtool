from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibNSNumber, NibLocalizableString
from xml.etree.ElementTree import Element
from .helpers import __xibparser_cell_flags, __xibparser_cell_options, handle_props, PropSchema, MAP_YES_NO, makeSystemColor
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSTextFieldCell", elem, parent)
    ctx.extraNibObjects.append(obj)

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSContents", attrib="title", default="", filter=NibString.intern, skip_default=False),
        PropSchema(prop="NSTextBezelStyle", attrib="bezelStyle", default="default_placeholder", map={"default_placeholder": 0, "round": 1}, skip_default=True),
    ])
    if ctx.isBaseLocalization:
        title = elem.attrib.get("title", "")
        obj["NSContents"] = NibLocalizableString(title, key=f"{elem.attrib.get('id', '')}.title")

    key = elem.attrib.get("key")
    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)

        obj["NSSupport"] = NibNil() # TODO
        obj["NSControlView"] = obj.xib_parent()
        if placeholder := elem.attrib.get("placeholderString"):
            obj["NSPlaceholderString"] = NibString.intern(placeholder)
        if (11759 <= ctx.toolsVersion <= 12107) or parent.extraContext.get("allowsCharacterPickerTouchBarItem"):
            obj["NSCharacterPickerEnabled"] = True
        if elem.attrib.get("drawsBackground") == "YES":
            obj["NSDrawsBackground"] = True
        parse_children(ctx, elem, obj)

        if obj.get("NSFormatter") is not None:
            contents = obj.get("NSContents")
            if isinstance(contents, (NibString, NibLocalizableString)) and contents._text.lstrip('-').isdigit():
                obj["NSContents"] = NibNSNumber(int(contents._text))

        text_color = obj.get("NSTextColor")
        bg_color = obj.get("NSBackgroundColor")
        if (ctx.toolsVersion <= 14268
                and elem.attrib.get("editable") == "YES"
                and text_color is not None and text_color.get("NSColorName") == NibString.intern("textColor")
                and bg_color is not None and bg_color.get("NSColorName") == NibString.intern("textBackgroundColor")):
            obj["NSTextColor"] = makeSystemColor("controlTextColor")

        parent["NSCell"] = obj

    elif key == "dataCell":
        parse_children(ctx, elem, obj)
        __xibparser_cell_flags(elem, obj, parent)

        obj["NSControlView"] = obj.xib_parent().xib_parent() # should be table not the column
        assert obj["NSControlView"].originalclassname() in ("NSTableView", "NSOutlineView"), obj["NSControlView"].originalclassname()

        parent["NSDataCell"] = obj

    else:
        raise Exception(f"unknown key {key}")

    return obj
