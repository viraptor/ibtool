from ..models import ArchiveContext, NibObject, XibObject, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from ..models import XibId

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    obj = XibObject(ctx, "NSNibOutletConnector", elem, parent)
    obj["NSSource"] = parent
    obj["NSDestination"] = XibId(elem.attrib.get("destination"))
    obj["NSLabel"] = elem.attrib.get("property")
    obj["NSChildControllerCreationSelectorName"] = NibNil()

    # Add this to the list of connections we'll have to resolve later.
    ctx.connections.append(obj)
