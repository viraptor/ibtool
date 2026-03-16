from ..models import ArchiveContext, NibObject, NibString, NibMutableList, NibList, XibId, XibObject
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    xibid = elem.attrib.get("id")
    if xibid and parent is not None:
        key = elem.attrib.get("key")
        if key == "safeArea":
            guide = XibObject(ctx, "NSLayoutGuide", elem, parent)
            guide["NSLayoutGuideIdentifier"] = NibString.intern("NSViewSafeAreaLayoutGuide")
            guide["NSShouldBeArchived"] = True
            guide["NSLayoutGuideNegativeSize"] = True
            guide["NSLayoutGuideLockedToOwningView"] = True
            guide["NSLayoutGuideSystemConstraints"] = NibMutableList([])
            ctx.addObject(XibId(xibid), guide)
            parent["IBNSSafeAreaLayoutGuide"] = NibObject("IBNSViewAutolayoutGuide", parent, {
                "IBNSLayoutGuideSystemType": 2,
            })
            if not parent.get("NSViewLayoutGuides"):
                parent["NSViewLayoutGuides"] = NibList([guide])
            else:
                parent["NSViewLayoutGuides"] = NibList(list(parent["NSViewLayoutGuides"]) + [guide])
        elif key == "layoutMargins":
            parent["IBNSLayoutMarginsGuide"] = NibObject("IBNSViewAutolayoutGuide", parent, {
                "IBNSLayoutGuideSystemType": 1,
            })
            ctx.addObject(XibId(xibid), parent)
