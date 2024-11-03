import std.mem;
import std.io;
import std.core;
import std.string;

using FlexNumber;

fn flex_value(ref FlexNumber num) {
    u32 res = 0;
    for (u8 i=0, i < sizeof(num.values), i=i+1){
        res = res + ((num.values[i] & 0x7f) << (i*7));
    }
    return res;
};

struct FlexNumber {
    u32 _location = $;
    u8 values[while($ == _location || std::mem::read_unsigned($-1, 1) & 0x80 == 0)];
} [[format_read("flex_value"),transform("flex_value")]];

struct Class {
    FlexNumber length;
    u8 tp;
    if(tp == 0x81) {
        u32 unknown;
    }
    char name[length];
};

fn class_mapping(ref FlexNumber idx) {
    return classes[idx].name;
};

struct ObjectEntry {
    FlexNumber class_idx [[format_read("class_mapping")]];
    FlexNumber props_first_idx;
    FlexNumber num_props;
} [[single_color]];

struct Label {
    FlexNumber length [[hidden]];
    char value[length];
} [[single_color,inline]];

enum Encoding : u8 {
    Byte = 0,
    Short = 1,
    Word = 2,
    DWord = 3,
    False = 4,
    True = 5,
    Float = 6,
    Double = 7,
    String = 8,
    Nil = 9,
    Object = 10,
};

fn label_mapping(ref FlexNumber idx) {
    return labels[idx].value;
};

fn object_ref(u32 id) {
    return std::format("@{}", id);
};

using Property;

fn prop_string(ref Property prop) {
    str label = labels[prop.label_idx].value;
    str type = std::string::substr(std::core::formatted_value(prop.encoding), 10, 20);
    if(std::core::has_member(prop, "value")) {
        return std::format("{}/{} ({})", label, prop.value, type);
    } else {
        return std::format("{}/{}", label, type);
    }
};

struct Property {
    FlexNumber label_idx [[format_read("label_mapping")]];
    Encoding encoding;
    match(encoding) {
        (Encoding::Byte): u8 value;
        (Encoding::Short): u16 value;
        (Encoding::Word): u32 value;
        (Encoding::DWord): u64 value;
        (Encoding::Float): float value;
        (Encoding::Double): double value;
        (Encoding::String): {
            FlexNumber length;
            char value[length];
        }
        (Encoding::Object): u32 value [[format_read("object_ref")]];
    }
} [[single_color,format_read("prop_string")]];

struct Section {
    u32 obj_count;
    u32 address;
};

struct Header {
    u32 size;
    u32 section_count = (size-1)/2;
    Section sections[section_count];
};

char magic[10]@0;
u32 unknown@10;
Header header@14;

Section cls_section = header.sections[3];
Class classes[cls_section.obj_count] @ cls_section.address;

Section objs_section = header.sections[0];
ObjectEntry objs[objs_section.obj_count] @ objs_section.address;

Section labels_section = header.sections[1];
Label labels[labels_section.obj_count] @ labels_section.address;

Section props_section = header.sections[2];
Property props[props_section.obj_count] @ props_section.address;
