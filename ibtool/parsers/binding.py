from ..models import ArchiveContext, NibObject, XibId, NibDictionary, NibNSNumber, NibString
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
        for k, v in x.attrib.items():
            if k == "key":
                continue
            data.append(NibString.intern(k))
            data.append(NibString.intern(v))
        for o in x:
            if o.tag == "integer":
                data.append(NibString.intern(o.attrib["key"]))
                data.append(NibNSNumber(int(o.attrib["value"])))
            elif o.tag == "string":
                data.append(NibString.intern(o.attrib["key"]))
                data.append(NibString.intern(o.text or ""))
            elif o.tag == "real":
                data.append(NibString.intern(o.attrib["key"]))
                data.append(NibNSNumber(float(o.attrib["value"])))
            elif o.tag == "bool":
                data.append(NibString.intern(o.attrib["key"]))
                data.append(NibNSNumber(o.attrib["value"] == "YES"))
            else:
                raise Exception(f"unknown tag: {o.tag}")
    if data:
        obj["NSOptions"] = NibDictionary(data)
    if previousBinding:
        obj["NSPreviousConnector"] = XibId(previousBinding)
    binding_id = elem.attrib.get("id")
    if binding_id:
        ctx.bindingConnectors[binding_id] = obj
    ctx.connections.append(obj)

