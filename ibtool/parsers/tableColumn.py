from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibData, NibList, NibMutableList, NibMutableSet, XibId, NibNSNumber
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, makeSystemColor
from ..parsers_base import parse_children
from ..genlib import CompileNibObjects

def _is_outline_column(column_elem, table_view):
    if table_view.originalclassname() != "NSOutlineView":
        return False
    return table_view.extraContext.get("outlineTableColumnId") == column_elem.attrib.get("id")

def _get_effective_col_width(column_obj, table_view):
    col_w = column_obj.get("NSWidth")
    if col_w is None:
        return None
    expansion = table_view.extraContext.get("expected_column_expansion", 0)
    if expansion > 0 and (column_obj.get("NSResizingMask") or 0) & 1:
        col_w = col_w + expansion
    return col_w

def _compile_prototype_cell_view(ctx, nested_ctx, column_elem, column_obj, table_view, nib_view):
    ics_w = table_view.get("NSIntercellSpacingWidth")
    if ics_w is None:
        ics_w = 3.0
    is_outline_col = _is_outline_column(column_elem, table_view)
    if is_outline_col:
        x_offset = int(ics_w) // 2 + 9
        col_w = _get_effective_col_width(column_obj, table_view)
        if col_w is not None:
            w_reduction = int(ics_w) * 5 // 2 + 8
            target_w = int(col_w - w_reduction)
        else:
            target_w = None
    else:
        x_offset = int((ics_w + 3) // 2)
        target_w = None

    nib_appl_parent = XibObject(nested_ctx, "NSCustomObject", None, None)
    nib_appl_parent["NSClassName"] = "NSObject"
    nib_appl = XibObject(nested_ctx, "NSCustomObject", None, nib_appl_parent)
    nib_appl["NSClassName"] = "NSApplication"

    identifier = nib_view.extraContext.get("identifier", column_elem.attrib.get("identifier", ""))
    nib_view._parent = nib_appl_parent
    nib_view["NSNextResponder"] = NibNil()
    nib_view["NSReuseIdentifierKey"] = NibString.intern(identifier)

    subviews = nib_view.get("NSSubviews")
    objects = [nib_appl_parent, nib_view]
    connections = []

    if subviews and len(subviews) > 0:
        nib_sub = subviews[0]
        objects.append(nib_sub)
        nib_sub_cell = nib_sub.get("NSCell")
        if nib_sub_cell:
            objects.append(nib_sub_cell)
        nib_outlet = XibObject(nested_ctx, "NSNibOutletConnector", None, None)
        nib_outlet["NSSource"] = nib_view
        nib_outlet["NSDestination"] = nib_sub
        nib_outlet["NSLabel"] = NibString.intern("textField")
        nib_outlet["NSChildControllerCreationSelectorName"] = NibNil()
        objects.append(nib_appl)
        objects.append(nib_outlet)
        connections.append(nib_outlet)
    else:
        objects.append(nib_appl)

    nib_data = CompileNibObjects([make_basic_nib(objects, root=nib_appl_parent, connections=connections)])

    nib_view._parent = column_obj

    if table_view.get("NSTableViewArchivedReusableViewsKey") is not None:
        table_view["NSTableViewArchivedReusableViewsKey"].addItem(NibString.intern(identifier))
        table_view["NSTableViewArchivedReusableViewsKey"].addItem(NibObject("NSNib", None, {
            "NSNibFileData": NibData(bytes(nib_data)),
            "NSNibFileImages": NibNil(),
            "NSNibFileIsKeyed": True,
            "NSNibFileSounds": NibNil(),
            "NSNibFileUseParentBundle": True,
        }))


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
        has_cell_views = obj.extraContext.get("prototypeCellViews") or obj.extraContext.get("prototypeCellView")
        nib_views = obj.extraContext.get("prototypeCellViews")
        if nib_views:
            sorted_views = sorted(nib_views, key=lambda v: v.extraContext.get("identifier", ""))
            for nib_view in sorted_views:
                _compile_prototype_cell_view(ctx, nested_ctx, elem, obj, parent, nib_view)
        nib_view = obj.extraContext.get("prototypeCellView")
        if nib_view:
            if parent.get("NSTableViewArchivedReusableViewsKey") is not None:
                parent["NSTableViewArchivedReusableViewsKey"].addItem(NibString.intern(elem.attrib.get("identifier", "")))
            # Compute cell view x offset from intercell spacing
            ics_w = parent.get("NSIntercellSpacingWidth")
            if ics_w is None:
                ics_w = 3.0
            is_outline_col = _is_outline_column(elem, parent)
            if is_outline_col:
                x_offset = int(ics_w) // 2 + 9
                col_w = _get_effective_col_width(obj, parent)
                if col_w is not None:
                    w_reduction = int(ics_w) * 5 // 2 + 8
                    target_w = int(col_w - w_reduction)
                else:
                    target_w = None
            else:
                x_offset = int((ics_w + 3) // 2)
                target_w = None

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
                new_w = target_w if target_w is not None else ec_frame[2]
                nib_view["NSFrame"] = NibString.intern(f"{{{{{new_x}, {ec_frame[1]}}}, {{{new_w}, {ec_frame[3]}}}}}")
                nib_view.extraContext["NSFrame"] = (new_x, ec_frame[1], new_w, ec_frame[3])
                if target_w is not None and new_w != ec_frame[2]:
                    nib_sub_frame = nib_sub.extraContext.get("NSFrame")
                    if nib_sub_frame and len(nib_sub_frame) == 4:
                        nib_sub["NSFrame"] = NibString.intern(f"{{{{{nib_sub_frame[0]}, {nib_sub_frame[1]}}}, {{{new_w}, {nib_sub_frame[3]}}}}}")
                        nib_sub.extraContext["NSFrame"] = (nib_sub_frame[0], nib_sub_frame[1], new_w, nib_sub_frame[3])

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
