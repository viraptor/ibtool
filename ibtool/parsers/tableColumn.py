from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibData, NibList, NibMutableList, NibMutableSet, XibId, NibNSNumber
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, makeSystemColor
from ..parsers_base import parse_children
from ..genlib import CompileNibObjects

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTableColumn", elem, parent, view_attributes=False)

    parse_children(ctx, elem, obj)

    # Column's editable attribute overrides any NSIsEditable set by child cells
    if elem.attrib.get("editable") == "NO" and obj.get("NSIsEditable"):
        del obj["NSIsEditable"]

    obj["NSIdentifier"] = NibString.intern(elem.attrib.get("identifier", ""))
    if max_width := elem.attrib.get("maxWidth"):
        obj["NSMaxWidth"] = float(max_width)
    if min_width := elem.attrib.get("minWidth"):
        obj["NSMinWidth"] = float(min_width)
    obj["NSTableView"] = parent
    if width := elem.attrib.get("width"):
        obj["NSWidth"] = float(width)

    if parent.originalclassname() in ("NSTableView", "NSOutlineView"):
        nested_ctx = ctx.nested_context()
        if parent.get("NSTableViewArchivedReusableViewsKey") is not None:
            parent["NSTableViewArchivedReusableViewsKey"].addItem(NibString.intern(elem.attrib.get("identifier", "")))
        nib_view = obj.extraContext.get("prototypeCellView")
        if nib_view:
            nib_appl_parent = XibObject(nested_ctx, "NSCustomObject", None, None)
            nib_appl_parent["NSClassName"] = "NSObject"
            nib_appl = XibObject(nested_ctx, "NSCustomObject", None, nib_appl_parent)
            nib_appl["NSClassName"] = "NSApplication"
            nib_view._parent = nib_appl
            nib_view["NSReuseIdentifierKey"] = NibString.intern(elem.attrib.get("identifier", ""))
            nib_sub = nib_view["NSSubviews"][0]
            nib_sub_cell = nib_sub["NSCell"]
            nib_data = CompileNibObjects([make_basic_nib([nib_appl_parent, nib_view, nib_sub, nib_sub_cell, nib_appl])])
            if parent.get("NSTableViewArchivedReusableViewsKey") is not None:
                parent["NSTableViewArchivedReusableViewsKey"].addItem(NibObject("NSNib", None, {
                    "NSNibFileData": NibData(bytes(nib_data)),
                    "NSNibFileImages": NibNil(),
                    "NSNibFileIsKeyed": True,
                    "NSNibFileSounds": NibNil(),
                    "NSNibFileUseParentBundle": True,
                }))
    else:
        raise Exception(f"Unexpected parent: {parent.originalclassname()}")

    return obj

def make_basic_nib(objects: list[NibObject]):
    oids_keys = [o for o in objects if isinstance(o, XibObject) and (o.xibid is None or not o.xibid.is_negative_id())]
    oids_values = [NibNSNumber(x+1) for x in range(len(oids_keys))]
    return NibObject("NSObject", None, {
        "IB.objectdata": NibObject("NSIBObjectData", None, {
            "NSAccessibilityConnectors": NibMutableList([]),
            "NSAccessibilityOidsKeys": NibList([]),
            "NSAccessibilityOidsValues": NibList([]),
            "NSObjectsKeys": NibList([o for o in objects if o.parent() is not None]),
            "NSObjectsValues": NibList([k.parent() for k in objects if k.parent() is not None]),
            "NSOidsKeys": NibList(oids_keys),
            "NSOidsValues": NibList(oids_values),
            "NSRoot": objects[0].parent() if objects else NibNil(),
            "NSConnections": NibMutableList(),
            "NSVisibleWindows": NibMutableSet(),
        }),
        "IB.systemFontUpdateVersion": 1
    })
