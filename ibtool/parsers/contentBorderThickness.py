from ..models import ArchiveContext
from xml.etree.ElementTree import Element


def parse(ctx: ArchiveContext, elem: Element, parent) -> None:
    min_y = elem.attrib.get("minY")
    if min_y is not None:
        parent["NSContentBorderThicknessMinY"] = float(min_y)
        parent["NSAutorecalculatesContentBorderThicknessMinY"] = False
    min_x = elem.attrib.get("minX")
    if min_x is not None:
        parent["NSContentBorderThicknessMinX"] = float(min_x)
        parent["NSAutorecalculatesContentBorderThicknessMinX"] = False
