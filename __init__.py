import math
import bpy
import platform

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
# from bpy_extras.io_utils import ImportHelper
# not sure what this brings us...

from . import import_fcstd

bl_info = {
    "name": "FreeBImport v02",
    "author": "s-light",
    "version": (0, 2, 0),
    "blender": (3, 0, 0),
    "location": "File > Import > FreeCAD (.FCStd)",
    "description": "Import FreeCAD .FCStd files to Blender",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

# brut force path loading:
# import sys; sys.path.append("/path/to/FreeCAD.so")


# ==============================================================================
# Blender Operator class
# ==============================================================================

# https://docs.blender.org/api/current/bpy.types.AddonPreferences.html#module-bpy.types


class IMPORT_OT_FreeCAD_Preferences(bpy.types.AddonPreferences):
    """A preferences settings dialog to set the path to the FreeCAD module."""

    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    # bl_idname = __name__
    bl_idname = __package__

    # Set platform-specific defaults
    if platform.system() == "Darwin":
        _default_freecad = "/Applications/FreeCAD.app/Contents/Resources/lib/"
        _default_system_packages = "/Applications/FreeCAD.app/Contents/Resources/lib/python3.11/site-packages"
    elif platform.system() == "Windows":
        _default_freecad = "C:\\Program Files\\FreeCAD 0.21\\bin"
        _default_system_packages = "C:\\Program Files\\FreeCAD 0.21\\bin\\Lib\\site-packages"
    else:
        _default_freecad = "/usr/lib/freecad-daily-python3/lib/FreeCAD.so"
        _default_system_packages = "/usr/lib/python3/dist-packages/"

    filepath_freecad: bpy.props.StringProperty(
        subtype="FILE_PATH",
        name="Path to FreeCAD lib",
        description=(
            "Path to \n" "FreeCAD.so (Mac/Linux) \n" "or \n" "FreeCAD.pyd (Windows)"
        ),
        default=_default_freecad,
    )
    filepath_system_packages: bpy.props.StringProperty(
        subtype="FILE_PATH",
        name="Path to system python modules",
        description=(
            "find with help of python console inside of FreeCAD:\n"
            ">>> import six\n"
            ">>> six.__file__\n"
            "'/usr/lib/python3/dist-packages/six.py'\n"
            "use first part: '/usr/lib/python3/dist-packages/'"
        ),
        default=_default_system_packages,
    )

    def draw(self, context):
        """Draw Preferences."""
        layout = self.layout
        layout.label(
            text=(
                "FreeCAD must be installed on your system, and its path set below."
                " Make sure both FreeCAD and Blender use the same Python version "
                "(check their Python console)"
            )
        )
        layout.prop(self, "filepath_freecad")
        layout.prop(self, "filepath_system_packages")
        layout.separator()
        layout.label(text="Report bugs or issues:")
        layout.operator("wm.url_open", text="Open GitHub Issues Page").url = "https://github.com/tankshield/FreeBimport"


# class IMPORT_OT_FreeCAD(bpy.types.Operator, ImportHelper):
class IMPORT_OT_FreeCAD(bpy.types.Operator):
    """Imports the contents of a FreeCAD .FCStd file."""

    bl_idname = "freebimportv02.import_freecad"
    bl_label = "Import FreeCAD FCStd file"
    bl_options = {"REGISTER", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".fcstd"

    # https://blender.stackexchange.com/a/7891/16634
    # see Text -> Templates -> Python -> Operator File Export
    filter_glob: bpy.props.StringProperty(
        default="*.FCStd; *.fcstd", options={"HIDDEN"},
    )

    # Properties assigned by the file selection window.
    directory: bpy.props.StringProperty(
        maxlen=1024, subtype="FILE_PATH", options={"HIDDEN", "SKIP_SAVE"},
    )
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"}
    )

    # user import options
    option_skiphidden: bpy.props.BoolProperty(
        name="Skip hidden objects",
        default=True,
        description="Only import objects that where visible in FreeCAD",
    )
    option_filter_sketch: bpy.props.BoolProperty(
        name="Filter Sketch objects",
        default=True,
        description="Filter Sketch objects out.",
    )
    option_update: bpy.props.BoolProperty(
        name="Update existing objects",
        default=True,
        description=(
            "Keep objects with same names in current scene and "
            "their materials, only replace the geometry"
        ),
    )
    option_update_only_modified_meshes: bpy.props.BoolProperty(
        name="Update only modified meshes",
        default=True,
        description=(
            "Only replace the geometry if the the source in FreeCAD has changed."
        ),
    )
    option_placement: bpy.props.BoolProperty(
        name="Use Placements",
        default=True,
        description="Set Blender pivot points to the FreeCAD placements",
    )
    option_tessellation: bpy.props.FloatProperty(
        name="Tessellation value",
        default=0.10,
        description="The tessellation value to apply when triangulating shapes",
    )
    option_triangulate_meshes: bpy.props.BoolProperty(
        name="Triangulate meshes",
        default=False,
        description="Triangulate all faces during import (may lose multi-material info)",
    )
    option_cleanup_after_import: bpy.props.BoolProperty(
        name="Cleanup after import",
        default=False,
        description="Apply Tris to Quads and Limited Dissolve operations after import",
    )
    option_auto_smooth_use: bpy.props.BoolProperty(
        name="Auto Smooth",
        default=True,
        description="activate auto_smooth on every imported mesh",
    )
    option_auto_smooth_angle: bpy.props.FloatProperty(
        name="Auto Smooth Angle",
        default=math.radians(30),
        soft_min=math.radians(1),
        soft_max=math.radians(180),
        subtype="ANGLE",
        unit="ROTATION",
        description="set auto_smooth_angle on every imported mesh",
    )
    option_scale: bpy.props.FloatProperty(
        name="Scaling value",
        precision=4,
        default=0.001,
        # soft_min=0.0001,
        # soft_max=1,
        description=(
            "A scaling value to apply to imported objects. "
            "Default value of 0.001 means one Blender unit = 1 meter"
        ),
    )
    option_sharemats: bpy.props.BoolProperty(
        name="Share similar materials",
        default=True,
        description=("Objects with same color/transparency will use the same material"),
    )
    # option_create_tree: bpy.props.BoolProperty(
    #     name="Recreate FreeCAD Object-Tree",
    #     default=True,
    #     description=(
    #         "Try to recreate the same parent-child relationships "
    #         "as in the FreeCAD Object-Tree."
    #     )
    # )
    option_obj_name_prefix: bpy.props.StringProperty(
        name="Prefix object names",
        maxlen=42,
        default="",
        description=("prefix for every object name." ""),
    )
    option_prefix_with_filename: bpy.props.BoolProperty(
        name="Prefix object names with filename",
        default=False,
        description=(
            "recommend for multi-file import. \n"
            "otherwise it can create name confusions."
            ""
        ),
    )
    option_links_as_col: bpy.props.BoolProperty(
        name="App::Link as Collection-Instances",
        default=False,
        description=(
            "create App::Link objects as Collection-Instances. \n"
            "therefore create Link-Targets as Collections. \n"
            "this means the instances can only have the original "
            "material of the Link-Target.\n"
            "\n"
            "if you deactivate this the importer creates `real objects` "
            "for every App::Link object - they share the mesh. "
            "this can get very deep tree if the Link-Targets are "
            "App::Part objects themself.."
            ""
        ),
    )

    def invoke(self, context, event):
        """Invoke is called when the user picks our Import menu entry."""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def get_preferences(self):
        """Get addon preferences."""
        print("__package__: '{}'".format(__package__))
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences
        return addon_prefs

    def get_path_to_freecad(self):
        """Get FreeCAD path from addon preferences."""
        # get the FreeCAD path specified in addon preferences
        addon_prefs = self.get_preferences()
        path = addon_prefs.filepath_freecad
        print("addon_prefs path_to freecad", path)
        return path

    def get_path_to_system_packages(self):
        """Get FreeCAD path from addon preferences."""
        # get the FreeCAD path specified in addon preferences
        addon_prefs = self.get_preferences()
        path = addon_prefs.filepath_system_packages
        print("addon_prefs path_to system_packages", path)
        return path

    # def get_path_to(self, target):
    #     """Get FreeCAD mod path from addon preferences."""
    #     # get the FreeCAD path specified in addon preferences
    #     addon_prefs = self.get_preferences()
    # i currently dont know how to do this...
    #     path = addon_prefs["filepath_" + target]
    #     print("addon_prefs path to " + target + " ", path)
    #     return path

    def execute(self, context):
        """Call when the user is done using the modal file-select window."""
        path_to_freecad = self.get_path_to_freecad()
        # path_to_system_packages = self.get_path_to("system_packages")
        path_to_system_packages = self.get_path_to_system_packages()
        dir = self.directory
        for file in self.files:
            filestr = str(file.name)
            if filestr.lower().endswith(".fcstd"):
                my_importer = import_fcstd.ImportFcstd(
                    update=self.option_update,
                    update_only_modified_meshes=self.option_update_only_modified_meshes,
                    placement=self.option_placement,
                    scale=self.option_scale,
                    tessellation=self.option_tessellation,
                    triangulate_meshes=self.option_triangulate_meshes,
                    cleanup_after_import=self.option_cleanup_after_import,
                    auto_smooth_use=self.option_auto_smooth_use,
                    auto_smooth_angle=self.option_auto_smooth_angle,
                    skiphidden=self.option_skiphidden,
                    filter_sketch=self.option_filter_sketch,
                    sharemats=self.option_sharemats,
                    update_materials=False,
                    obj_name_prefix=self.option_obj_name_prefix,
                    obj_name_prefix_with_filename=self.option_prefix_with_filename,
                    links_as_collectioninstance=self.option_links_as_col,
                    path_to_freecad=path_to_freecad,
                    path_to_system_packages=path_to_system_packages,
                    report=self.report,
                )
                return my_importer.import_fcstd(filename=dir + filestr)
        return {"FINISHED"}


# ==============================================================================
# Register plugin with Blender
# ==============================================================================

classes = (
    IMPORT_OT_FreeCAD,
    IMPORT_OT_FreeCAD_Preferences,
)


def menu_func_import(self, context):
    """Needed if you want to add into a dynamic menu."""
    self.layout.operator(IMPORT_OT_FreeCAD.bl_idname, text="FreeBImport v02 (.FCStd)")


def register():
    """Register."""
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    """Unregister."""
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
