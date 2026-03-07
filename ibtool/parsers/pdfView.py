from ..models import ArchiveContext, NibObject, XibObject, NibString, NibFloat, NibMutableList, NibMutableSet
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "PDFView", elem, parent)
    parse_children(ctx, elem, obj)

    obj["NSSuperview"] = obj.xib_parent()
    obj.setIfEmpty("NSSubviews", NibMutableList([]))
    obj["NSDragTypes"] = NibMutableSet([NibString.intern("NSFilenamesPboardType")])
    obj["Version"] = 3
    obj["DisplayMode"] = 1
    obj["PageBreaks"] = elem.attrib.get("displaysPageBreaks", "YES") != "NO"
    obj["ScaleFactor"] = NibFloat(1.0)
    obj["AutoScale"] = elem.attrib.get("autoScales") == "YES"
    obj["DisplayDirection"] = False
    obj["DisplaysRTL"] = False
    obj["MinScaleFactor"] = NibFloat(0.10000000149011612)
    obj["MaxScaleFactor"] = NibFloat(20.0)
    obj["DisplaysAsBook"] = False
    obj["EnableDataDetectors"] = False
    obj["InterpolationQuality"] = 2
    obj["AcceptsDraggedFiles"] = False

    # PDFView always gets WIDTH_SIZABLE | HEIGHT_SIZABLE
    obj.flagsOr("NSvFlags", vFlags.WIDTH_SIZABLE | vFlags.HEIGHT_SIZABLE)

    return obj
