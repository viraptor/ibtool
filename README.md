# ibtool
Opensource, cleanroom reimplemention of Apple's `ibtool`.
Based on davidquesada's initial implementation for iOS, fixed up for use with MacOS projects.

## Usage
Currently, ibtool supports only compiling XIB files and
printing NIB files in a readable way. (only for MacOS)

    Usage: ibtool.py [OPTIONS] input-file
      --dump                       dump the contents of a NIB file in a readable format
      --compile <output pathname>  compile a XIB or storyboard file to a binary format
      -e                           show type encodings when dumping a NIB file
      -s sort the object keys to avoid issues when comparing different files

If no command is specified, ibtool will assume --dump,
i.e. `ibtool.py --dump somefile.nib` and `ibtool.py somefile.nib` are equivalent.

## Notes
The set of Interface Builder features supported by this application is very limited,
and requires specific functionalities to be manually added, so certain usages of
unimplemented views, scenes, layout constraints, or size classes may fail to compile
or result in NIBs that are missing functionality.

## Development
This project includes samples of xib/nib pairs which compile correctly and can be run using `./test.sh`. To submit new code, ideally: 
- existing files still pass
- a new sample which previously failed is added

### Compatibility
The compatibility is maintained at the level of the code interface. This means the following must be identical to Apple's tool:
- types of objects
- keys and values
- length of the encoded integer values
- array order (apart from the constraints)

What we don't care about: 
- serialised class order
- order of object keys
- constraints, which both have their own explicit priority and seem to have a very implementation-specific order (although if you understand the order, please help fixing it)
- order of objects in the file - those don't depend on the IDs and have their own order in the top level object anyway

### Adding new functionality
If the current version doesn't compile something correctly, the best way to approach it is to create a minimal example for it in the interface builder. Then put that for in the samples directory and compile a corresponding `nib` file using upstream `ibtool --compile foo.nib foo.xib`. After that you can use `./test.sh samples/foo.xib` to see the mismatched values.
