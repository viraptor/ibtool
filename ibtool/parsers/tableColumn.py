from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibData, NibList, NibMutableList, NibMutableSet, XibId, NibNSNumber
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, makeSystemColor
from ..parsers_base import parse_children
from ..genlib import CompileNibObjects

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTableColumn", elem, parent, view_attributes=False)
    obj["NSTableView"] = parent

    parse_children(ctx, elem, obj)

    # Columns are editable by default; only remove when explicitly disabled
    if elem.attrib.get("editable") == "NO":
        if obj.get("NSIsEditable"):
            del obj["NSIsEditable"]
    else:
        obj.setIfEmpty("NSIsEditable", True)

    obj["NSIdentifier"] = NibString.intern(elem.attrib.get("identifier", ""))
    if max_width := elem.attrib.get("maxWidth"):
        obj["NSMaxWidth"] = float(max_width)
    if min_width := elem.attrib.get("minWidth"):
        obj["NSMinWidth"] = float(min_width)
    if width := elem.attrib.get("width"):
        obj["NSWidth"] = float(width)

    if parent.originalclassname() in ("NSTableView", "NSOutlineView"):
        nested_ctx = ctx.nested_context()
        if parent.get("NSTableViewArchivedReusableViewsKey") is not None:
            parent["NSTableViewArchivedReusableViewsKey"].addItem(NibString.intern(elem.attrib.get("identifier", "")))
        nib_view = obj.extraContext.get("prototypeCellView")
        if nib_view:
            # Compute cell view x offset from intercell spacing
            ics_w = parent.get("NSIntercellSpacingWidth")
            if ics_w is None:
                ics_w = 3.0
            x_offset = int((ics_w + 3) // 2)

            # Create sub-nib scaffold objects
            nib_appl_parent = XibObject(nested_ctx, "NSCustomObject", None, None)
            nib_appl_parent["NSClassName"] = "NSObject"
            nib_appl = XibObject(nested_ctx, "NSCustomObject", None, nib_appl_parent)
            nib_appl["NSClassName"] = "NSApplication"

            # Cell view parent in sub-nib is NSObject (not NSApplication)
            nib_view._parent = nib_appl_parent
            nib_view["NSNextResponder"] = NibNil()
            nib_view["NSReuseIdentifierKey"] = NibString.intern(elem.attrib.get("identifier", ""))

            nib_sub = nib_view["NSSubviews"][0]
            nib_sub_cell = nib_sub["NSCell"]

            # Create outlet connector for sub-nib (textField → first subview)
            nib_outlet = XibObject(nested_ctx, "NSNibOutletConnector", None, None)
            nib_outlet["NSSource"] = nib_view
            nib_outlet["NSDestination"] = nib_sub
            nib_outlet["NSLabel"] = NibString.intern("textField")
            nib_outlet["NSChildControllerCreationSelectorName"] = NibNil()

            # Shift cell view x based on intercell spacing (applies to both sub-nib and top-level)
            ec_frame = nib_view.extraContext.get("NSFrame")
            if ec_frame and len(ec_frame) == 4 and x_offset > 0:
                new_x = ec_frame[0] + x_offset
                nib_view["NSFrame"] = NibString.intern(f"{{{{{new_x}, {ec_frame[1]}}}, {{{ec_frame[2]}, {ec_frame[3]}}}}}")
                nib_view.extraContext["NSFrame"] = (new_x, ec_frame[1], ec_frame[2], ec_frame[3])

            # Compile sub-nib
            objects = [nib_appl_parent, nib_view, nib_sub, nib_sub_cell, nib_appl, nib_outlet]
            nib_data = CompileNibObjects([make_basic_nib(objects, root=nib_appl_parent, connections=[nib_outlet])])

            # Restore top-level parent to table column and remove sub-nib-only key
            nib_view._parent = obj
            del nib_view["NSReuseIdentifierKey"]

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

def make_basic_nib(objects: list[NibObject], root=None, connections=None):
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
            "NSRoot": root if root is not None else (objects[0].parent() if objects else NibNil()),
            "NSConnections": NibMutableList(connections) if connections else NibMutableList(),
            "NSVisibleWindows": NibMutableSet(),
        }),
        "IB.systemFontUpdateVersion": 1
    })
