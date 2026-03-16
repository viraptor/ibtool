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
        # Set sub-nib specific properties on subviews
        subnib_restore = []  # (obj, key, old_value_or_sentinel)
        _SENTINEL = object()
        def _set_subnib_flags(view):
            svs = view.get("NSSubviews")
            if not svs:
                return
            for sv in svs:
                if hasattr(sv, 'extraContext') and sv.extraContext.get("NSDoNotTranslateAutoresizingMask"):
                    if sv.get("NSDoNotTranslateAutoresizingMask") is None:
                        sv["NSDoNotTranslateAutoresizingMask"] = True
                        subnib_restore.append((sv, "NSDoNotTranslateAutoresizingMask", _SENTINEL))
                cell = sv.get("NSCell")
                if cell and hasattr(cell, 'originalclassname') and cell.originalclassname() == "NSImageCell":
                    old_val = cell.get("NSAnimates")
                    if old_val is not True:
                        subnib_restore.append((cell, "NSAnimates", old_val))
                        cell["NSAnimates"] = True
                _set_subnib_flags(sv)
        _set_subnib_flags(nib_view)

        # Collect all objects for sub-nib in the order matching Apple's ibtool:
        # For each subview: view, cell, then that view's constraints
        # Then cell view constraints, then NSApplication
        seen = {id(nib_view)}

        def _collect_view_group(view):
            """Collect a view, its cell, and its constraints in order."""
            svs = view.get("NSSubviews")
            if not svs:
                return
            for sv in svs:
                if id(sv) not in seen:
                    seen.add(id(sv))
                    objects.append(sv)
                cell = sv.get("NSCell")
                if cell and id(cell) not in seen:
                    seen.add(id(cell))
                    objects.append(cell)
                # Add this subview's own constraints
                sv_constraints = sv.get("NSViewConstraints")
                if sv_constraints and hasattr(sv_constraints, '_items'):
                    for c in sv_constraints._items:
                        if isinstance(c, NibObject) and id(c) not in seen:
                            seen.add(id(c))
                            objects.append(c)
                # Recurse into nested subviews
                _collect_view_group(sv)

        _collect_view_group(nib_view)

        # Cell view's own constraints last
        cv_constraints = nib_view.get("NSViewConstraints")
        if cv_constraints and hasattr(cv_constraints, '_items'):
            for c in cv_constraints._items:
                if isinstance(c, NibObject) and id(c) not in seen:
                    seen.add(id(c))
                    objects.append(c)

        nib_sub = subviews[0]
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

    # Restore sub-nib specific properties
    for obj_ref, key, old_val in subnib_restore:
        if old_val is _SENTINEL:
            del obj_ref[key]
        else:
            obj_ref[key] = old_val

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

            nib_appl_parent = XibObject(nested_ctx, "NSCustomObject", None, None)
            nib_appl_parent["NSClassName"] = "NSObject"
            nib_appl = XibObject(nested_ctx, "NSCustomObject", None, nib_appl_parent)
            nib_appl["NSClassName"] = "NSApplication"

            nib_view._parent = nib_appl_parent
            nib_view["NSNextResponder"] = NibNil()
            nib_view["NSReuseIdentifierKey"] = NibString.intern(elem.attrib.get("identifier", ""))

            nib_sub = nib_view["NSSubviews"][0]
            nib_sub_cell = nib_sub["NSCell"]

            nib_outlet = XibObject(nested_ctx, "NSNibOutletConnector", None, None)
            nib_outlet["NSSource"] = nib_view
            nib_outlet["NSDestination"] = nib_sub
            nib_outlet["NSLabel"] = NibString.intern("textField")
            nib_outlet["NSChildControllerCreationSelectorName"] = NibNil()

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

            objects = [nib_appl_parent, nib_view, nib_sub, nib_sub_cell, nib_appl, nib_outlet]
            nib_data = CompileNibObjects([make_basic_nib(objects, root=nib_appl_parent, connections=[nib_outlet])])

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
    # Collect ALL reachable XibObjects for NSOidsKeys (not just explicit objects)
    seen_ids = set()
    oids_keys = []
    def _collect_oids(obj):
        obj_id = id(obj)
        if obj_id in seen_ids:
            return
        seen_ids.add(obj_id)
        if isinstance(obj, XibObject) and (obj.xibid is None or not obj.xibid.is_negative_id()):
            oids_keys.append(obj)
        if isinstance(obj, NibObject):
            for _, v in obj.getKeyValuePairs():
                if isinstance(v, NibObject):
                    _collect_oids(v)
                elif hasattr(v, '_items'):
                    for item in v._items:
                        if isinstance(item, NibObject):
                            _collect_oids(item)
    for obj in objects:
        _collect_oids(obj)
    if connections:
        for conn in connections:
            _collect_oids(conn)
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
