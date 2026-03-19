from ..models import ArchiveContext, NibObject, NibNil, NibString, NibList, NibNSNumber, NibMutableList
from xml.etree.ElementTree import Element


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    values = []
    key_paths = []
    for attr in elem:
        if attr.tag != "userDefinedRuntimeAttribute":
            continue
        key_path = attr.attrib.get("keyPath", "")
        attr_type = attr.attrib.get("type", "")
        key_paths.append(NibString.intern(key_path))

        if attr_type == "number":
            value_elem = attr.find("real")
            if value_elem is not None:
                values.append(NibNSNumber(float(value_elem.attrib.get("value", "0"))))
            else:
                bool_elem = attr.find("bool")
                if bool_elem is not None:
                    values.append(NibNSNumber(bool_elem.attrib.get("value") == "YES"))
                else:
                    int_elem = attr.find("integer")
                    if int_elem is not None:
                        values.append(NibNSNumber(int(int_elem.attrib.get("value", "0"))))
                    else:
                        values.append(NibNSNumber(0))
        elif attr_type == "boolean":
            values.append(NibNSNumber(attr.attrib.get("value") == "YES"))
        elif attr_type == "string":
            values.append(NibString.intern(attr.attrib.get("value", "")))
        elif attr_type == "point":
            point_elem = attr.find("point")
            if point_elem is not None:
                values.append(NibString.intern(f'{{{point_elem.attrib.get("x", "0")}, {point_elem.attrib.get("y", "0")}}}'))
            else:
                values.append(NibString.intern("{0, 0}"))
        elif attr_type == "size":
            size_elem = attr.find("size")
            if size_elem is not None:
                values.append(NibString.intern(f'{{{size_elem.attrib.get("width", "0")}, {size_elem.attrib.get("height", "0")}}}'))
            else:
                values.append(NibString.intern("{0, 0}"))
        elif attr_type == "rect":
            rect_elem = attr.find("rect")
            if rect_elem is not None:
                values.append(NibString.intern(f'{{{{{rect_elem.attrib.get("x", "0")}, {rect_elem.attrib.get("y", "0")}}}, {{{rect_elem.attrib.get("width", "0")}, {rect_elem.attrib.get("height", "0")}}}}}'))
            else:
                values.append(NibString.intern("{{0, 0}, {0, 0}}"))
        elif attr_type == "color":
            color_elem = attr.find("color")
            if color_elem is not None:
                values.append(NibNil())
            else:
                values.append(NibNil())
        else:
            values.append(NibNil())

    if values:
        connector = NibObject("NSIBUserDefinedRuntimeAttributesConnector", parent)
        connector["NSObject"] = parent
        connector["NSValues"] = NibList(values)
        connector["NSKeyPaths"] = NibList(key_paths)
        ctx.connections.append(connector)
