from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSStepper", elem, parent)
    obj["NSSuperview"] = parent

    parse_children(ctx, elem, obj)

    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlSize"] = 0
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlTextAlignment"] = 0
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 0x10002
    obj["NSEnabled"] = True

    # These stepper-level properties are always defaults (actual values are on the cell)
    obj["NSStepperMinValue"] = 0.0
    obj["NSStepperMaxValue"] = 0.0
    obj["NSStepperIncrement"] = 0.0
    obj["NSStepperWraps"] = False
    obj["NSStepperAutorepeat"] = False

    # NSControlContinuous comes from the cell's continuous attribute
    cell = obj.get("NSCell")
    if cell and cell.extraContext.get("continuous"):
        obj["NSControlContinuous"] = True
    else:
        obj["NSControlContinuous"] = False

    return obj
