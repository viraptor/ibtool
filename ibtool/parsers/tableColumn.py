from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibData, NibList, NibMutableList, NibMutableSet
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, makeSystemColor
from ..parsers_base import parse_children
from ..genlib import CompileNibObjects

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTableColumn", elem, parent, view_attributes=False)

    parse_children(ctx, elem, obj)

    obj["NSIdentifier"] = NibString.intern(elem.attrib.get("identifier", ""))
    if max_width := elem.attrib.get("maxWidth"):
        obj["NSMaxWidth"] = float(max_width)
    if min_width := elem.attrib.get("minWidth"):
        obj["NSMinWidth"] = float(min_width)
    obj["NSTableView"] = parent
    if width := elem.attrib.get("width"):
        obj["NSWidth"] = float(width)

    if parent.originalclassname() == "NSTableView":
        parent["NSTableViewArchivedReusableViewsKey"].addItem(NibString.intern(elem.attrib.get("identifier", "")))
        nib_root = NibObject("NSCustomObject", None, {
            "NSClassName": "NSObject",
        })
        nib_cell_view = NibObject("NSTableCellView", nib_root, {
            "IBNSClipsToBounds": 0,
            "IBNSLayoutMarginsGuide": NibNil(),
            "IBNSSafeAreaLayoutGuide": NibNil(),
            "NSFrame": NibString("123"),
            "NSNextResponder": NibNil(),
            "NSNibTouchBar": NibNil(),
            "NSReuseIdentifierKey": obj["NSIdentifier"],
            "NSViewWantsBestResolutionOpenGLSurface": True,
            "NSSubviews": NibMutableList(),
            "NSvFlags": 0x112,
        })
        nib_cell_view_sub = NibObject("NSTextField", nib_cell_view, {
            "IBNSClipsToBounds": 0,
            "IBNSLayoutMarginsGuide": NibNil(),
            "IBNSSafeAreaLayoutGuide": NibNil(),
            "NSAllowsLogicalLayoutDirection": False,
            "NSAllowsWritingTools": True,
            "NSAntiCompressionPriority": NibString.intern("{250, 750}"),
            "NSControlContinuous": False,
            "NSControlLineBreakMode": 4,
            "NSControlRefusesFirstResponder": False,
            "NSControlSendActionMask": 4,
            "NSControlSize": 0,
            "NSControlSize2": 0,
            "NSControlTextAlignment": 4,
            "NSControlUsesSingleLineMode": False,
            "NSControlWritingDirection": -1,
            "NSEnabled": True,
            "NSFrame": NibString.intern("{12345}"),
            "NSHuggingPriority": NibString.intern("{23456}"),
            "NSNextResponder": nib_cell_view,
            "NSNibTouchBar": NibNil(),
            "NSSuperview": nib_cell_view,
            "NSTextFieldAlignmentRectInsetsVersion": 2,
            "NSViewWantsBestResolutionOpenGLSurface": True,
            "NSvFlags": 0x12a,
        })
        nib_cell_view["NSSubviews"].addItem(nib_cell_view_sub)
        nib_cell_view_sub_cell = NibObject("NSTextFieldCell", nib_cell_view_sub, {
            "NSCellFlags": 0x4000040,
            "NSCellFlags2": 0x10400800,
            "NSContents": NibString("Table View Cell"),
            "NSControlSize2": 0,
            "NSControlView": nib_cell_view_sub,
            "NSBackgroundColor": makeSystemColor("textBackgroundColor"),
            "NSSupport": NibObject("NSFont"),
            "NSTextColor": makeSystemColor("controlTextColor"),
        })
        nib_cell_view_sub["NSCell"] = nib_cell_view_sub_cell
        nib_appl = NibObject("NSCustomObject", nib_root, {
            "NSClassName": "NSApplication",
        })
        nib_data = CompileNibObjects([make_basic_nib([nib_cell_view, nib_cell_view_sub, nib_cell_view_sub_cell, nib_appl])])
        parent["NSTableViewArchivedReusableViewsKey"].addItem(NibObject("NSNib", None, {
            "NSNibFileData": NibData(bytes(nib_data)),
            "NSNibFileImages": NibNil(),
            "NSNibFileIsKeyed": True,
            "NSNibFileSounds": NibNil(),
            "NSNibFileUseParentBundle": True,
        }))

    return obj

def make_basic_nib(objects: list[NibObject]):
    return NibObject("NSObject", None, {
        "IB.objectdata": NibObject("NSIBObjectData", None, {
            "NSAccessibilityConnectors": NibMutableList([]),
            "NSAccessibilityOidsKeys": NibList([]),
            "NSAccessibilityOidsValues": NibList([]),
            "NSObjectsKeys": NibList(objects),
            "NSObjectsValues": NibList([k.parent() for k in objects]),
            "NSOidsKeys": NibList([]),
            "NSOidsValues": NibList([]),
            "NSRoot": objects[0].parent() if objects else NibNil(),
            "NSConnections": NibMutableList(),
            "NSVisibleWindows": NibMutableSet(),
        }),
        "IB.systemFontUpdateVersion": 1
    })
