from ..models import ArchiveContext
from xml.etree.ElementTree import Element


def _fragment_text(frag: Element) -> str:
    if "content" in frag.attrib:
        return frag.attrib["content"]
    for child in frag:
        if child.tag in ("string", "mutableString") and child.attrib.get("key") == "content":
            return child.text or ""
    return ""


def parse(ctx: ArchiveContext, elem: Element, parent) -> None:
    text = "".join(
        _fragment_text(child)
        for child in elem if child.tag == "fragment"
    )
    parent.extraContext["attributedStringText"] = text
