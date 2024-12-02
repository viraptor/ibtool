from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibDictionary, NibNSNumber, NibMutableList, NibMutableString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, makeSystemColor
from ..parsers_base import parse_children
from ..constants import TVFlags
import re

def __parse_size(size: str) -> tuple[int, int]:
    return tuple(int(x) for x in re.findall(r'-?\d+', size))

def __parse_pos_size(size: str) -> tuple[int, int, int, int]:
    return tuple(int(x) for x in re.findall(r'-?\d+', size))

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTextView", elem, parent)
    
    editable = 0x2 if elem.attrib.get("editable", "YES") == "YES" else 0
    imports_graphics = 0x8 if elem.attrib.get("importsGraphics") == "YES" else 0
    spelling_correction = 0x4000000 if elem.attrib.get("spellingCorrection") == "YES" else 0
    rich_text = 0x4 if elem.attrib.get("richText", "YES") == "YES" else 0
    smart_insert_delete = 0x200 if elem.attrib.get("smartInsertDelete") == "YES" else 0
    horizontally_resizable = TVFlags.HORIZONTALLY_RESIZABLE if elem.attrib.get("horizontallyResizable") == "YES" else 0
    vertically_resizable = TVFlags.VERTICALLY_RESIZABLE if elem.attrib.get("verticallyResizable", "YES" if ctx.toolsVersion < 23504 else "NO") == "YES" else 0
    preferred_find_style = {
        None: None,
        "panel": 1,
        "bar": 2,
    }[elem.attrib.get("findStyle")]
    preferred_find_style_flag = {
        None: 0,
        "panel": 0x2000,
        "bar": 0,
    }[elem.attrib.get("findStyle")]

    shared_data = XibObject(ctx, "NSTextViewSharedData", None, obj)
    shared_data["NSAutomaticTextCompletionDisabled"] = False
    shared_data["NSBackgroundColor"] = NibNil()
    shared_data["NSDefaultParagraphStyle"] = NibNil()
    shared_data["NSFlags"] = 0x901 | spelling_correction | editable | imports_graphics | rich_text | smart_insert_delete | preferred_find_style_flag
    shared_data["NSInsertionColor"] = makeSystemColor('textInsertionPointColor')
    shared_data["NSLinkAttributes"] = NibDictionary([
        NibString.intern("NSColor"),
        makeSystemColor("linkColor"),
        NibString.intern("NSCursor"),
        NibObject("NSCursor", None, {
            "NSCursorType": 13,
            "NSHotSpot": NibString.intern("{8, -8}"),
        }),
        NibString.intern("NSUnderline"),
        NibNSNumber(1),
    ])
    shared_data["NSMarkedAttributes"] = NibNil()
    shared_data["NSMoreFlags"] = 0x1
    shared_data["NSPreferredTextFinderStyle"] = 0
    shared_data["NSSelectedAttributes"] = NibDictionary([
        NibString.intern("NSBackgroundColor"),
        makeSystemColor("selectedTextBackgroundColor"),
        NibString.intern("NSColor"),
        makeSystemColor("selectedTextColor"),
    ])
    shared_data["NSTextCheckingTypes"] = 0
    shared_data["NSTextFinder"] = NibNil()
    if preferred_find_style is not None:
        shared_data["NSPreferredTextFinderStyle"] = preferred_find_style
    obj["NSSharedData"] = shared_data
    obj["NSSuperview"] = obj.xib_parent()

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    obj["NSDelegate"] = NibNil()
    obj["NSTVFlags"] = 132 | horizontally_resizable | vertically_resizable
    obj["NSNextResponder"] = obj.xib_parent()
    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    text_container = NibObject("NSTextContainer", obj)
    text_container["NSLayoutManager"] = NibNil()
    text_container["NSMinWidth"] = 15.0
    text_container["NSTCFlags"] = 0x1

    layout_manager = NibObject("NSLayoutManager", text_container)
    layout_manager["NSTextContainers"] = NibMutableList([text_container])
    layout_manager["NSLMFlags"] = 0x66
    layout_manager["NSDelegate"] = NibNil()
    layout_manager["NSTextStorage"] = NibObject("NSTextStorage", layout_manager, {
        "NSDelegate": NibNil(),
        "NSString": NibMutableString(""),
    })
    text_container["NSLayoutManager"] = layout_manager
    text_container["NSTextLayoutManager"] = NibNil()

    text_container["NSTextView"] = obj
    if frame_size := obj.get("NSFrameSize"):
        text_container["NSWidth"] = float(__parse_size(frame_size._text)[0])
    elif frame := obj.get("NSFrame"):
        text_container["NSWidth"] = float(__parse_pos_size(frame._text)[2])
    else:
        text_container["NSWidth"] = 1.0

    obj["NSTextContainer"] = text_container

    if ctx.toolsVersion < 23504:
        obj.setIfEmpty("NSTextViewTextColor", makeSystemColor("textColor"))

    return obj

