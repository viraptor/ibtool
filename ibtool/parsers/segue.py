from ..models import ArchiveContext, NibObject, XibObject, XibId
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    kind = elem.get("kind")
    relationship = elem.get("relationship")
    destination_id = elem.get("destination")

    if kind == "relationship" and destination_id:
        ctx.segueConnections.append({
            "relationship": relationship,
            "destination": XibId(destination_id),
            "source": parent,
        })
