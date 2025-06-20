<!--lint disable list-item-indent-->
<!--lint disable list-item-bullet-indent-->

# FreeBImport_v01

**This is a fork of [io_import_fcstd](https://github.com/s-light/io_import_fcstd) by Yorik van Havre.**

blender importer for FreeCAD files

---

## About this fork

- Original author: Yorik van Havre ([io_import_fcstd](https://github.com/s-light/io_import_fcstd))
- This fork was completely updated using [Cursor](https://www.cursor.so/) to add compatibility and new functionality for Blender 4.4, and to remove all unnecessary files and code for a cleaner, modern add-on experience.
- Maintained by: tankshield

---

# Description

This script imports FreeCAD .FCStd files into Blender.  
This is a work in progress, so not all geometry elements of FreeCAD might be supported at this point.

# Installation

1. Download this repository as a ZIP file (or clone it).
2. In Blender, go to `Edit` > `Preferences` > `Add-ons` > `Install...` and select the ZIP file.
3. Enable the add-on (search for "FreeBImport").
4. Set the correct paths to FreeCAD libraries in the add-on preferences:

### Default FreeCAD library paths

#### macOS
- **FreeCAD library path:**
  `/Applications/FreeCAD.app/Contents/Resources/lib/`
- **System Python packages path:**
  `/Applications/FreeCAD.app/Contents/Resources/lib/python3.11/site-packages`

#### Windows
- **FreeCAD library path:**
  `C:\Program Files\FreeCAD 0.21\bin`
- **System Python packages path:**
  `C:\Program Files\FreeCAD 0.21\bin\Lib\site-packages`

> Make sure the Python version used by Blender matches the one used by FreeCAD (the first two version numbers must match, e.g., 3.11.x).

5. To test your setup, open Blender's Python console and run:

```python
import FreeCAD
```
If no error appears, your paths are set up correctly.

# Usage

Go to `File > Import > FreeBImport (.FCStd)` and select your FreeCAD file.

# Working with...
This add-on has only been tested under macOS Sequoia on Intel platform. It remains untested on other platforms (Windows, Linux, Apple Silicon, etc.). Please report your experience if you try it elsewhere.

# Known Issues

**Blender may crash on exit after importing a FreeCAD file.**

This is a known issue caused by the way FreeCAD and its OpenCASCADE libraries are loaded into Blender's process. When Blender closes, unloading these libraries can cause a segmentation fault (SIGSEGV) or crash. This is a limitation of mixing FreeCAD and Blender in the same process and is not specific to this add-on.

**Workarounds:**
- Save your Blender project immediately after importing.
- Restart Blender after each import session to avoid losing work.
- The crash does not affect the imported data if you save before quitting.

For more details, see the crash report in the Error Reporting folder.

# License
MIT License. See [LICENSE](./LICENSE).

# Original Project
Forked from [io_import_fcstd](https://github.com/s-light/io_import_fcstd) by Yorik van Havre.

# TODO
see the [issues for open points](https://github.com/s-light/io_import_fcstd/issues).

- support clones
- support texts, dimensions, etc (non-part/mesh objects)
