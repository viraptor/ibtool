from ..models import ArchiveContext, NibObject, XibId, NibMutableDictionary, NibNSNumber, NibString
from .helpers import handle_props, PropSchema
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None

    previousBinding = elem.attrib.get("previousBinding")

    obj = NibObject("NSNibBindingConnector", parent)
    handle_props(ctx, elem, obj, [
        PropSchema("NSDestination", attrib="destination", filter=XibId),
        PropSchema("NSSource", const=parent.xibid),
        PropSchema("NSBinding", attrib="name"),
        PropSchema("NSLabel", const=f"{elem.attrib['name']}: {elem.attrib['keyPath']}"),
        PropSchema("NSKeyPath", attrib="keyPath"),
        PropSchema("NSNibBindingConnectorVersion", const=2)
    ])
    data = []
    for x in elem.iter("dictionary"):
        for o in x:
            if o.tag == "integer":
                data.append(NibString.intern(o.attrib["key"]))
                data.append(NibNSNumber(int(o.attrib["value"])))
            else:
                raise Exception(f"unknown tag: {x.tag}")
    if data:
        obj["NSOptions"] = NibMutableDictionary(data)
    ctx.connections.append(obj)

