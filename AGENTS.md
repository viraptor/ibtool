## CLI Interface

Entry point: `ibtool/__main__.py` -> `run()`

```
ibtool input.xib --compile output.nib   # Compile XIB to NIB
ibtool input.nib --dump                  # Dump NIB contents
ibtool input.nib --dump -t               # Dump NIB as a tree view
ibtool input.nib --compare other.nib     # Diff two NIB files
ibtool input.nib --compare other.nib --xib source.xib  # Diff with XIB id annotations
ibtool input.xib --xibmap               # Show XIB element id -> NIB object index mapping
```

### Debugging tools

- **`--dump`**: Dumps the binary NIB contents as flat key-value pairs. Add `-t` for a hierarchical tree view, `-s` to sort keys, `-e` to show encoding types, `-f PATH` to filter to a specific structure path (segments separated by `/`).
- **`--compare`**: Diffs two NIB files structurally, reporting mismatched classes, missing keys, and value differences. Add `--xib source.xib` to annotate diff output with `[xib:ID]` tags showing which XIB element each differing object came from.
- **`--xibmap`**: Parses a XIB file, compiles it internally, and prints a table mapping each XIB element id to its compiled NIB object index and class name. Useful for understanding which XIB elements correspond to which NIB objects when investigating `--compare` output.

## Compilation Pipeline

```
XIB (XML) -> xibparser.py -> parsers/* -> models (NibObject tree) -> genlib.py -> NIB (binary)
```

1. **`xibparser.py`** - Reads the XIB XML, iterates over top-level `<objects>` elements.
2. **`parsers_base.py`** - Dispatches each XML element to the correct parser by tag name. `parse_children()` recurses into child elements (constraints are always processed last to match Apple's ordering).
3. **`parsers/*`** - ~80 parser modules, one per XML element type. Each has a `parse(ctx, elem, parent)` function that creates `NibObject`/`XibObject` instances and sets their properties.
4. **`models.py`** - Core data structures: `NibObject` (property bag), `XibObject` (extends NibObject with XIB-specific state like xibid, parent tracking, frame calculation), `ArchiveContext` (parsing state: object registry, connections, constraints).
5. **`genlib.py`** - Serializes the NibObject tree into the binary NIB format.

## Parser Structure

Parsers live in `ibtool/parsers/`. Each module is registered in `parsers/__init__.py` with a mapping from XML tag name to module. The `all` dict drives dispatch.

A parser's `parse()` function typically:
1. Creates an object via `make_xib_object(ctx, "NSClassName", elem, parent)`
2. Calls `parse_children(ctx, elem, obj)` to recurse
3. Sets properties on the object
4. Returns the object

### `handle_props` - Preferred Property Abstraction

Prefer `handle_props` when writing or modifying parsers to set properties declaratively, replacing ad-hoc imperative property assignments.

Location: `ibtool/parsers/helpers.py`

```python
from .helpers import handle_props, PropSchema, MAP_YES_NO

handle_props(ctx, elem, obj, [
    PropSchema(prop="NSBoxType", attrib="boxType", default=None, map=BOX_TYPE_MAP, skip_default=False),
    PropSchema(prop="NSTransparent", const=False),
    PropSchema(prop="NSRowHeight", attrib="rowHeight", default="16", filter=float),
])
```

`PropSchema` fields:

| Field | Purpose |
|-------|---------|
| `prop` | NIB property name to set on the object |
| `attrib` | XML attribute name to read from the element |
| `const` | Set a constant value (ignores XML) |
| `default` | Default value when the XML attribute is absent. Also used as a fill-in when no `attrib` or `const` - sets the prop only if it's currently unset. |
| `map` | Dict mapping XML attribute values to NIB property values |
| `filter` | Callable to transform the value (e.g. `float`, `int`) |
| `skip_default` | If `True` (default), skip setting the property when the value equals the default |
| `or_mask` | Bitwise OR - accumulates flag bits into the property |

**Common patterns:**

- **Constant**: `PropSchema(prop="NSTransparent", const=False)` - always sets to False
- **Direct mapping**: `PropSchema(prop="NSEnabled", attrib="enabled", default="YES", map=MAP_YES_NO)` - reads XML attr, maps YES/NO to True/False
- **Flags accumulation**: Multiple PropSchemas with the same `prop` and different `or_mask` values build up a flags field incrementally. First set initial bits with `const`, then conditionally OR in more bits:
  ```python
  PropSchema(prop="NSTvFlags", const=TVFLAGS.UNKNOWN_1 | TVFLAGS.ALLOWS_COLUMN_RESIZING),
  PropSchema(prop="NSTvFlags", attrib="multipleSelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_MULTIPLE_SELECTION),
  ```
- **Type conversion**: `PropSchema(prop="NSRowHeight", attrib="rowHeight", default="16", filter=float)`
- **Default fill**: `PropSchema(prop="NSSubviews", default=NibMutableList([]))` - sets only if prop not already set

See `parsers/box.py` and `parsers/tableView.py` for good examples.

Compare against `parsers/button.py` which uses older imperative style - new code should prefer `handle_props`.

## Key Models

- **`NibObject`** - Base property bag. Properties accessed via `obj["key"]` / `obj["key"] = val`. Methods: `setIfEmpty()`, `setIfNotDefault()`, `flagsOr()`, `flagsAnd()`, `append()`, `extend()`.
- **`XibObject`** - Extends NibObject. Has `xibid` (XML id), `extraContext` dict for parser-local state, parent tracking via `xib_parent()`, `frame()` for layout calculation.
- **`ArchiveContext`** - Parsing session state. Tracks all objects by xibid, manages connections (outlets/actions), constraints, autolayout mode. Methods: `addObject()`, `findObject()`, `getObject()`, `resolveConnections()`.
- **`NibString`** / **`NibData`** - Interned immutable wrappers. Use `NibString.intern("value")`.
- **`NibMutableList`**, **`NibMutableDictionary`**, etc. - Collection types for NIB serialization.

## Development process

When given a new xib file with errors to fix up:
1. Run `./test.py path/to/the/file.xib` (supports multiple)
2. Create a minimal reproduction test for one of the issues in samples/debug/ and compile that file using /usr/bin/ibtool (only use it with directories below current - /tmp and other paths can't be accessed)
3. Either implement the fix or go back to step 2 for more tests if the issue is more complex
4. The isolate issue is fixed, move the samples/debug/*.[nx]ib files into samples/correct/ to use as a regression test in the future.
5. Go back to step 1, until all issues are fixed (do not copy the original large xib file into samples/correct/)

Do NOT modity the original xib file in any way.

Order of fixing things:
- if there are collections with mismatched elements, fix this first, even if with basic stubs (to align comparison responses)
- if there are type differences, fix those
- fix simple missing arguments to reduce noise
- then fix node ordering if needed
- if any dependencies on toolchain version ranges were added, tighten them using binary search for the precise threshold

## Testing

`test.py` compiles sample XIB files and compares output against reference NIB files using `--compare`. Sample files are in `samples/`.
Rules for comparison: the structure of objects/keys and their order matters, the types matter. Exceptions: the order of connections and constraints can be ignored because the order seems to be an irrelevant implementation detail in the original tool.
To fix the implementation, you should do what test.py does and compare our result nib with the provided one. Never modify the nib or xib files in the samples directory.

## Code

Do NOT include comments which repeat the code itself. Only comment if the reason behind the code segment needs to be explained.
