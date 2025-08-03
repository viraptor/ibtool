from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibData, NibList, NibMutableList, NibMutableSet, XibId
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
        nib_view = obj.extraContext.get("prototypeCellView")
        if nib_view:
            nib_appl = NibObject("NSCustomObject", NibObject("NSCustomObject", None, {"NSClassName": "NSObject"}), {
                "NSClassName": "NSApplication",
            })
            nib_view._parent = nib_appl
            nib_view["NSReuseIdentifierKey"] = NibString.intern(elem.attrib.get("identifier", ""))
            nib_sub = nib_view["NSSubviews"][0]
            nib_sub_cell = nib_sub["NSCell"]
            nib_data = CompileNibObjects([make_basic_nib([nib_view, nib_sub, nib_sub_cell, nib_appl])])
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
