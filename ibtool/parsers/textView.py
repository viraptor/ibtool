from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibDictionary, NibNSNumber, NibMutableList, NibMutableString, NibMutableDictionary
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
    
    selectable = 0x1 if elem.attrib.get("selectable", "YES") == "YES" else 0
    editable = 0x2 if elem.attrib.get("editable", "YES") == "YES" else 0
    imports_graphics = 0x8 if elem.attrib.get("importsGraphics", "YES") != "NO" else 0
    spelling_correction = 0x4000000 if elem.attrib.get("spellingCorrection") == "YES" else 0
    rich_text = 0x4 if elem.attrib.get("richText", "YES") == "YES" else 0
    continuous_spell_checking = 0x80 if elem.attrib.get("continuousSpellChecking") == "YES" else 0
    smart_insert_delete = 0x200 if elem.attrib.get("smartInsertDelete") == "YES" else 0
    link_detection = 0x40000 if elem.attrib.get("linkDetection") == "YES" else 0
    horizontally_resizable = TVFlags.HORIZONTALLY_RESIZABLE if elem.attrib.get("horizontallyResizable") == "YES" else 0
    vertically_resizable = TVFlags.VERTICALLY_RESIZABLE if elem.attrib.get("verticallyResizable", "YES" if 11169 <= ctx.toolsVersion < 13087 else "NO") == "YES" else 0
    uses_font_panel = 0x20 if elem.attrib.get("usesFontPanel", "NO") == "YES" else 0
    uses_ruler = 0x40 if elem.attrib.get("usesRuler", "NO") == "YES" else 0
    allows_undo = 0x400 if elem.attrib.get("allowsUndo", "NO") == "YES" else 0
    draws_background = 0x800
    allows_document_background_change = 0x4000 if elem.attrib.get("allowsDocumentBackgroundColorChange", "NO") == "YES" else 0
    unknown_0x100 = 0x100 if elem.attrib.get("drawsBackground", "YES") != "NO" else 0
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
    storyboard_defaults = 0x2008000 if ctx.isStoryboard else 0
    custom_class_flags = 0x5020000 if elem.attrib.get("customClass") else 0
    shared_data["NSFlags"] = unknown_0x100 | draws_background | (spelling_correction if not ctx.isStoryboard else 0) | editable | imports_graphics | rich_text | continuous_spell_checking | smart_insert_delete | link_detection | preferred_find_style_flag | uses_font_panel | allows_document_background_change | uses_ruler | selectable | allows_undo | storyboard_defaults | custom_class_flags
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
        NibNSNumber(1.0 if ctx.toolsVersion < 10000 else 1),
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
    shared_data["NSWritingToolsFlags"] = 0x100
    shared_data["NSTextHighlightAttributes"] = NibNil()
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
    storage_text = obj.extraContext.get("attributedStringText", "")
    storage_props = {
        "NSDelegate": NibNil(),
        "NSString": NibMutableString(storage_text),
    }
    if storage_text:
        default_font = NibObject("NSFont", None, {
            "NSName": NibString.intern("Helvetica"),
            "NSSize": 12.0,
            "NSfFlags": 16,
        })
        storage_props["NSAttributes"] = NibDictionary([
            NibString.intern("NSColor"),
            makeSystemColor("textColor"),
            NibString.intern("NSFont"),
            default_font,
        ])
    layout_manager["NSTextStorage"] = NibObject("NSTextStorage", layout_manager, storage_props)
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

    clip_view = obj.xib_parent()
    if clip_view and clip_view.originalclassname() == "NSClipView":
        scroll_view = clip_view.xib_parent()
        if scroll_view and scroll_view.originalclassname() == "NSScrollView":
            sv_frame = scroll_view.extraContext.get("NSFrame") or scroll_view.extraContext.get("NSFrameSize")
            if sv_frame:
                sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
                sv_h = sv_frame[3] if len(sv_frame) == 4 else sv_frame[1]
                max_size = obj.extraContext.get("maxSize")
                if max_size:
                    max_w = int(max_size[0])
                    if max_w <= sv_w:
                        obj["NSMaxSize"] = f'{{{sv_w}, {max_size[1]}}}'
                elif not obj.get("NSMaxSize"):
                    obj["NSMaxSize"] = f'{{{sv_w}, {sv_h}}}'

    has_attributed_string = any(child.tag == "attributedString" for child in elem)
    if ctx.toolsVersion < 14269 and not has_attributed_string:
        obj.setIfEmpty("NSTextViewTextColor", makeSystemColor("textColor"))

    return obj

