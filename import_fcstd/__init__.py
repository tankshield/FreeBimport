#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Import FreeCAD files to blender."""

import sys
import bpy
import os
import math

# import pprint

from .. import freecad_helper as fc_helper
from .. import blender_helper as b_helper

from . import helper
from . import guidata
from .material import MaterialManager


# set to True to triangulate all faces (will loose multimaterial info)
TRIANGULATE = False


class ImportFcstd(object):
    """Import fcstd files."""

    def __init__(
        self,
        *,  # this forces named_properties..
        # filename=None,
        update=True,
        update_only_modified_meshes=True,
        placement=True,
        scale=0.001,
        tessellation=0.10,
        triangulate_meshes=False,
        cleanup_after_import=False,
        auto_smooth_use=True,
        auto_smooth_angle=math.radians(30),
        skiphidden=True,
        filter_sketch=True,
        sharemats=True,
        update_materials=False,
        obj_name_prefix="",
        obj_name_prefix_with_filename=False,
        links_as_collectioninstance=True,
        path_to_freecad=None,
        path_to_system_packages=None,
        report=None,
    ):
        """Init."""
        super(ImportFcstd, self).__init__()
        self.config = {
            "filename": None,
            "update": update,
            "update_only_modified_meshes": update_only_modified_meshes,
            "placement": placement,
            "tessellation": tessellation,
            "triangulate_meshes": triangulate_meshes,
            "cleanup_after_import": cleanup_after_import,
            "auto_smooth_use": auto_smooth_use,
            "auto_smooth_angle": auto_smooth_angle,
            "skiphidden": skiphidden,
            "filter_sketch": filter_sketch,
            "scale": scale,
            "sharemats": sharemats,
            "update_materials": update_materials,
            "obj_name_prefix_with_filename": obj_name_prefix_with_filename,
            "obj_name_prefix": obj_name_prefix,
            "links_as_collectioninstance": links_as_collectioninstance,
            "report": self.print_report,
        }
        self.path_to_freecad = path_to_freecad
        self.path_to_system_packages = path_to_system_packages
        self.report = report

        print("config", self.config)
        self.doc = None
        self.doc_filename = None
        self.guidata = {}

        self.fcstd_collection = None
        self.link_targets = None
        self.fcstd_empty = None

        self.imported_obj_names = []

        self.typeid_filter_list = [
            "GeoFeature",
            "PartDesign::CoordinateSystem",
        ]
        if self.config["filter_sketch"]:
            self.typeid_filter_list.append("Sketcher::SketchObject")

    def print_report(self, mode, data, pre_line=""):
        """Multi print handling."""
        b_helper.print_multi(
            mode=mode, data=data, pre_line=pre_line, report=self.report,
        )

    def format_obj(self, obj, pre_line="", post_line=""):
        """Print object with nice formating."""
        message = ""

        message = fc_helper.format_obj(
            obj=obj,
            pre_line=pre_line,
            show_lists=False,
            show_list_details=False,
            tight_format=True,
        )
        message += post_line
        return message

    def print_obj(self, obj, pre_line="", post_line="", end="\n"):
        """Print object with nice formating."""
        message = ""

        message = self.format_obj(obj=obj)
        message += post_line
        # print(message, end=end)
        self.config["report"]({"INFO"}, message, pre_line)

    def print_debug_report(self):
        """print out some minimal debug things.."""
        print("print_debug_report")
        import FreeCAD
        print("FreeCAD version:", FreeCAD.Version())
        objects = FreeCAD.ActiveDocument.Objects
        print("doc.Objects", len(objects))
        for o in objects:
            print(o, o.Name)

    def handle_label_prefix(self, label):
        """Handle all label prefix processing."""
        if label:
            prefix = self.config["obj_name_prefix"]
            if self.config["obj_name_prefix_with_filename"]:
                prefix = self.doc.Name + "__" + prefix
            if prefix:
                label = prefix + "__" + label
        return label

    def get_obj_label(self, obj):
        """Get object label with optional prefix."""
        label = None
        if obj:
            # obj_label = "NONE"
            # obj_label = obj.Label
            # label = obj_label
            label = obj.Label
        label = self.handle_label_prefix(label)
        return label

    def get_obj_link_target_label(self, obj):
        """Get object label with optional prefix."""
        label = None
        if obj:
            label = obj.Label + "__lt"
        label = self.handle_label_prefix(label)
        return label

    def get_obj_linkedobj_label(self, obj):
        """Get linkedobject label with optional prefix."""
        label = None
        if hasattr(obj, "LinkedObject"):
            label = "NONE"
            if obj.LinkedObject:
                label = obj.LinkedObject.Label
        label = self.handle_label_prefix(label)
        return label

    def get_obj_combined_label(self, parent_obj, obj):
        """Get object label with optional prefix."""
        label = None
        obj_label = "NONE"
        parent_obj_label = "NONE"
        if obj:
            obj_label = obj.Label
        if parent_obj:
            parent_obj_label = parent_obj.Label
        label = parent_obj_label + "." + obj_label
        label = self.handle_label_prefix(label)
        return label

    # def get_sub_obj_label(self, pre_line, func_data, parent_obj, obj):
    def get_sub_obj_label(self, pre_line, func_data, obj):
        """Get sub object label."""
        # print(
        #     pre_line
        #     + "get_sub_obj_label"
        # )
        # pre_line += ". "
        # print(
        #     pre_line
        #     + "func_data['obj_label']: "
        #     + b_helper.colors.fg.orange
        #     + "'{}'".format(func_data["obj_label"])
        #     + b_helper.colors.reset
        # )
        # print(
        #     pre_line
        #     + "func_data['link_source']: "
        #     + b_helper.colors.fg.orange
        #     + self.format_obj(func_data["link_source"])
        #     + b_helper.colors.reset
        # )
        # print(
        #     pre_line
        #     + "parent_obj              "
        #     + b_helper.colors.fg.orange
        #     + self.format_obj(parent_obj)
        #     + b_helper.colors.reset
        # )
        # print(
        #     pre_line
        #     + "       obj              "
        #     + b_helper.colors.fg.orange
        #     + self.format_obj(obj)
        #     + b_helper.colors.reset
        # )
        # obj_label = self.get_obj_combined_label(parent_obj, obj)
        # if func_data["obj_label"]:
        #     obj_label = (
        #         func_data["obj_label"]
        #         + "."
        #         + obj_label
        #     )
        obj_label = self.get_obj_label(obj)
        if func_data["link_source"]:
            obj_label = (
                # func_data["obj_label"]
                self.get_obj_label(func_data["link_source"])
                + "."
                + obj_label
            )
        return obj_label

    def fix_link_target_name(self, bobj):
        """Fix name of link target object."""
        bobj.name = bobj.name + "__lt"
        return bobj.name

    def check_obj_visibility(self, obj):
        """Check if obj is visible."""
        result = True
        if obj.Name in self.guidata and "Visibility" in self.guidata[obj.Name]:
            if self.guidata[obj.Name]["Visibility"] is False:
                result = False
        return result

    def check_obj_visibility_with_skiphidden(self, obj, obj_visibility=None):
        """Check if obj is visible."""
        result = True
        if self.config["skiphidden"]:
            # print("obj_visibility: '{}'".format(obj_visibility))
            if obj_visibility is not None:
                result = obj_visibility
            else:
                result = self.check_obj_visibility(obj)
        return result

    def check_collections_for_bobj(self, bobj):
        """Search all collections for given bobj."""
        found_in_collections = None
        for col in bpy.data.collections:
            if bobj.name in col.objects:
                if found_in_collections is None:
                    found_in_collections = []
                found_in_collections.append(col.name)
        return found_in_collections

    # ##########################################
    # object handling

    def hascurves(self, shape):
        """Check if shape has curves."""
        import Part

        for e in shape.Edges:
            if not isinstance(e.Curve, (Part.Line, Part.LineSegment)):
                return True
        return False

    def handle_placement(
        self,
        pre_line,
        obj,
        bobj,
        # enable_import_scale=False,
        enable_scale=True,
        relative=False,
        negative=False,
    ):
        """Handle placement."""
        if self.config["placement"]:
            # print(pre_line)
            # print(pre_line + "   §§§   §§§   handle_placement: '{}'".format(bobj.name))
            # print(pre_line)
            new_loc = obj.Placement.Base * self.config["scale"]
            # attention: multiply does in-place change.
            # so if you call it multiple times on the same value
            # you get really strange results...
            # new_loc = obj.Placement.Base.multiply(self.config["scale"])
            if relative:
                # print(
                #     "x: {} + {} = {}"
                #     "".format(
                #         bobj.location.x,
                #         new_loc.x,
                #         bobj.location.x + new_loc.x
                #     )
                # )
                if negative:
                    bobj.location.x = bobj.location.x - new_loc.x
                    bobj.location.y = bobj.location.y - new_loc.y
                    bobj.location.z = bobj.location.z - new_loc.z
                else:
                    bobj.location.x = bobj.location.x + new_loc.x
                    bobj.location.y = bobj.location.y + new_loc.y
                    bobj.location.z = bobj.location.z + new_loc.z
            else:
                bobj.location = new_loc
            m = bobj.rotation_mode
            bobj.rotation_mode = "QUATERNION"
            if obj.Placement.Rotation.Angle:
                # FreeCAD Quaternion is XYZW while Blender is WXYZ
                q = (obj.Placement.Rotation.Q[3],) + obj.Placement.Rotation.Q[:3]
                bobj.rotation_quaternion = q
                bobj.rotation_mode = m
            if enable_scale and ("Scale" in obj.PropertiesList):
                # object has Scale property so lets use it :-)
                bobj.scale = bobj.scale * obj.Scale

    def reset_placement_position(self, bobj):
        """Reset placement position."""
        bobj.location.x = 0
        bobj.location.y = 0
        bobj.location.z = 0

    def update_tree_collections(self, func_data):
        """Update object tree."""
        pre_line = func_data["pre_line"]
        bobj = func_data["bobj"]
        # col = self.check_collections_for_bobj(bobj)
        if func_data["collection"]:
            add_to_collection = False
            if self.config["update"]:
                if bobj.name not in func_data["collection"].objects:
                    add_to_collection = True
                else:
                    # print(
                    #     pre_line +
                    #     "'{}' already in collection '{}'"
                    #     "".format(bobj.name, func_data["collection"])
                    # )
                    pass
            else:
                add_to_collection = True

            if add_to_collection:
                func_data["collection"].objects.link(bobj)
                # print(
                #     pre_line +
                #     "'{}' add (tree_collections) to  '{}' "
                #     "".format(bobj, func_data["collection"])
                # )
        if not self.check_collections_for_bobj(bobj):
            # link to import collection - so that the object is visible.
            collection = self.fcstd_collection
            collection.objects.link(bobj)
            print(
                pre_line + "'{}' add (tree_parents) to '{}' "
                "".format(bobj, collection)
            )

    def update_tree_parents(self, func_data):
        """Update object tree."""
        pre_line = func_data["pre_line"]
        bobj = func_data["bobj"]
        # print(pre_line + "update_tree_parents")
        # print(pre_line + "  bobj.parent '{}'".format(bobj.parent))
        # print(
        #     pre_line + "  func_data[parent_bobj] '{}'".format(func_data["parent_bobj"])
        # )
        if bobj.parent is None and func_data["parent_bobj"] is not None:
            print(
                pre_line + "update_tree_parents" + "  obj '{}' set parent to '{}' "
                "".format(bobj, func_data["parent_bobj"])
            )
            # print(
            #     pre_line + "  obj '{}' set parent to '{}' "
            #     "".format(bobj, func_data["parent_bobj"])
            # )
            bobj.parent = func_data["parent_bobj"]
            # TODO: check 'update'

    def create_bmesh_from_func_data(
        self, func_data, obj_label, enable_import_scale=True
    ):
        """Create new object from bmesh."""
        bmesh = bpy.data.meshes.new(name=obj_label)
        bmesh.from_pydata(func_data["verts"], func_data["edges"], func_data["faces"])
        bmesh.update()
        # handle import scalling
        if enable_import_scale:
            scale = self.config["scale"]
            for v in bmesh.vertices:
                v.co *= scale
        bmesh.update()
        bmesh["freecad_mesh_hash"] = func_data["freecad_mesh_hash"]
        return bmesh

    def create_bobj_from_bmesh(self, func_data, obj_label, bmesh):
        """Create new object from bmesh."""
        bobj = bpy.data.objects.new(obj_label, bmesh)
        # check if we already used the bmesh.
        # if bmesh.name in bpy.data.meshes:
        #     print(
        #         func_data["pre_line"] +
        #         " ignore material import. mesh already existed."
        #     )
        # else:
        if len(bmesh.materials) <= 0:
            material_manager = MaterialManager(
                guidata=self.guidata,
                func_data=func_data,
                bobj=bobj,
                obj_label=obj_label,
                sharemats=self.config["sharemats"],
                report=self.config["report"],
                report_preline=func_data["pre_line"] + "| ",
            )
            material_manager.create_new()
        else:
            print(
                func_data["pre_line"]
                + " ignore material import. mesh already has material."
            )
        func_data["bobj"] = bobj
        return bobj

    def create_or_get_bmesh(self, pre_line, func_data, mesh_label):
        """Create or get bmesh."""
        pre_line_orig = func_data["pre_line"]
        print(pre_line_orig + "create_or_get_bmesh")
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line

        bmesh = None
        # bmesh_old_name = None
        bmesh_import = True

        print(pre_line + "mesh_label:", mesh_label)
        # print(pre_line + "bpy.data.meshes ({})".format(len(bpy.data.meshes)))
        # for mesh in bpy.data.meshes:
        #     print(pre_line + " - ", mesh)
        if mesh_label in bpy.data.meshes:
            bmesh = bpy.data.meshes[mesh_label]
            print(pre_line + "use found bmesh.")
            bmesh_import = False
            # print(
            #     pre_line
            #     + "bmesh.freecad_mesh_hash ",
            #     bmesh.get("freecad_mesh_hash", None)
            # )
            # print(
            #     pre_line
            #     + "func_data[freecad_mesh_hash] ",
            #     func_data["freecad_mesh_hash"]
            # )
            # print(pre_line + "mesh_label", mesh_label)
            # print(pre_line + "self.imported_obj_names")
            # for obj_name in self.imported_obj_names:
            #     print(pre_line + " - ", obj_name)
            if mesh_label not in self.imported_obj_names and self.config["update"]:
                if self.config["update_only_modified_meshes"]:
                    print(pre_line + "update_only_modified_meshes: TODO")
                    # bmesh.get("freecad_mesh_hash", None)
                    # func_data["freecad_mesh_hash"]
                # rename old mesh -
                # this way the new mesh can get the original name.
                helper.rename_old_data(bpy.data.meshes, mesh_label)
                # bmesh_old_name = helper.rename_old_data(bpy.data.meshes, mesh_label)
                bmesh_import = True
        # create bmesh
        if bmesh_import:
            print(pre_line + "import bmesh.")
            bmesh = self.create_bmesh_from_func_data(
                func_data, mesh_label, enable_import_scale=True
            )
            # print(pre_line + "create_bmesh_from_func_data: ", bmesh)
            # Auto smooth will be applied after import using Blender's internal functionality
            if mesh_label not in self.imported_obj_names:
                self.imported_obj_names.append(mesh_label)
        # return (bmesh, bmesh_old_name)
        func_data["pre_line"] = pre_line_orig
        return bmesh

    def create_or_update_bobj(self, pre_line, func_data, obj_label, bmesh):
        """Create or update bobj."""
        pre_line_orig = func_data["pre_line"]
        print(pre_line_orig + "create_or_update_bobj")
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line
        bobj = None
        is_new = False
        bobj_import = True
        # locate existing object (object with same name)
        if obj_label in bpy.data.objects:
            bobj = bpy.data.objects[obj_label]
            print(pre_line + "found bobj!")
            bobj_import = False
            if obj_label not in self.imported_obj_names and self.config["update"]:
                print(
                    pre_line + "Replacing existing object mesh: {}" "".format(obj_label)
                )
                # update only the mesh of existing object.
                # print(self.imported_obj_names)
                if len(bmesh.materials) <= 0:
                    # TODO: fix this!!
                    # correctly handle multimaterials
                    # copy old materials to new mesh:
                    for mat in bobj.data.materials:
                        bmesh.materials.append(mat)
                bobj.data = bmesh
                # self.handle_material_update(func_data, bobj)
                bobj_import = False
        # create bobj
        if bobj_import:
            # print(
            #     pre_line +
            #     "create_bobj_from_bmesh: '{}'"
            #     "".format(obj_label)
            # )
            bobj = self.create_bobj_from_bmesh(func_data, obj_label, bmesh)
            is_new = True
            # print(
            #     pre_line +
            #     "created new bobj: {}"
            #     "".format(bobj)
            # )
        func_data["pre_line"] = pre_line_orig
        return (is_new, bobj)

    def add_or_update_blender_obj(self, func_data):
        """Create or update object with mesh and material data."""
        """
            What should happen?
                check if we have the mesh already
                if not create
                check if we have the object already
                if not create it
        """
        pre_line_orig = func_data["pre_line"]
        print(pre_line_orig + "add_or_update_blender_obj")
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line

        obj_label = self.get_obj_label(func_data["obj"])
        mesh_label = obj_label
        if func_data["is_link"] and func_data["obj_label"]:
            obj_label = func_data["obj_label"]

        # print(pre_line + "obj_label", obj_label)
        # print(pre_line + "mesh_label", mesh_label)
        # print(pre_line + "obj", self.format_obj(func_data["obj"]))

        bmesh = self.create_or_get_bmesh(pre_line, func_data, mesh_label)

        is_new, bobj = self.create_or_update_bobj(pre_line, func_data, obj_label, bmesh)

        if self.config["update"] or is_new:
            # if func_data["obj"].isDerivedFrom("Part::Feature"):
            #     print(pre_line + "       obj isDerivedFrom Part::Feature")
            # if func_data["obj"].isDerivedFrom("App::Part"):
            #     print(pre_line + "       obj isDerivedFrom App::Part")
            # if func_data["parent_obj"].isDerivedFrom("Part::Feature"):
            #     print(pre_line + "parent_obj isDerivedFrom Part::Feature")
            # if func_data["parent_obj"].isDerivedFrom("App::Part"):
            #     print(pre_line + "parent_obj isDerivedFrom App::Part")

            if func_data["is_link"]:
                # print(pre_line + "is link")
                if func_data["obj"].isDerivedFrom("Part::Feature") and func_data[
                    "parent_obj"
                ].isDerivedFrom("App::Part"):
                    # print(
                    #     pre_line +
                    #     "is_link "
                    #     "&& obj is Part::Feature "
                    #     "&& parent_obj is App::Part "
                    # )
                    self.handle_placement(pre_line, func_data["obj"], bobj)
            else:
                # print(pre_line + "is not link")
                self.handle_placement(pre_line, func_data["obj"], bobj)

        if bobj.name not in self.imported_obj_names:
            self.imported_obj_names.append(bobj.name)
        func_data["bobj"] = bobj
        func_data["pre_line"] = pre_line_orig

    def sub_collection_add_or_update(self, func_data, collection_label):
        """Part-Collection handle add or update."""
        print(
            func_data["pre_line"]
            + "sub_collection_add_or_update: '{}'".format(collection_label)
        )
        temp_collection = None
        if self.config["update"]:
            if collection_label in bpy.data.collections:
                temp_collection = bpy.data.collections[collection_label]
        else:
            helper.rename_old_data(bpy.data.collections, collection_label)

        if not temp_collection:
            # create new
            temp_collection = bpy.data.collections.new(collection_label)
            func_data["collection"].children.link(temp_collection)
            print(
                func_data["pre_line"] + "'{}' add to '{}' "
                "".format(func_data["bobj"], func_data["collection"],)
            )
        else:
            # bpy.context.scene.collection.children.link(self.fcstd_collection)
            pass

        # update func_data links
        func_data["collection_parent"] = func_data["collection"]
        func_data["collection"] = temp_collection

    def set_obj_parent_and_collection(self, pre_line, func_data, bobj):
        """Set Object parent and collection."""
        bobj.parent = func_data["parent_bobj"]
        print(
            pre_line + "'{}' set parent to '{}' "
            "".format(bobj, func_data["parent_bobj"])
        )

        # add object to current collection
        collection = func_data["collection"]
        if not collection:
            collection = self.fcstd_collection
        if bobj.name not in collection.objects:
            collection.objects.link(bobj)
            # print(
            #     pre_line +
            #     "'{}' add to '{}' "
            #     "".format(bobj, collection)
            # )

    def parent_empty_add_or_update(self, func_data, empty_label):
        """Parent Empty handle add or update."""
        print(
            func_data["pre_line"]
            + "parent_empty_add_or_update: '{}'".format(empty_label)
        )
        pre_line = func_data["pre_line"] + " → "
        empty_bobj = None

        obj = func_data["obj"]

        print(
            pre_line + "current parent_obj ", self.format_obj(func_data["parent_obj"])
        )

        if empty_label in bpy.data.objects:
            # print(
            #     pre_line +
            #     "'{}' already in objects list.".format(empty_label)
            # )
            if self.config["update"]:
                empty_bobj = bpy.data.objects[empty_label]
                # print(
                #     pre_line +
                #     "update: '{}'".format(empty_bobj)
                # )
            else:
                renamed_to = helper.rename_old_data(bpy.data.objects, empty_label)
                print(pre_line + "overwrite - renamed to " "'{}'".format(renamed_to))

        flag_new = False
        if empty_bobj is None:
            print(pre_line + "create new empty_bobj '{}'".format(empty_label))
            empty_bobj = bpy.data.objects.new(name=empty_label, object_data=None)
            empty_bobj.empty_display_size = self.config["scale"] * 10
            self.set_obj_parent_and_collection(pre_line, func_data, empty_bobj)

        if self.config["update"] or flag_new:
            # set position of empty
            if obj:
                self.handle_placement(
                    pre_line, obj, empty_bobj,
                )
                # NOT HERE.
                # if not func_data["is_link"]:
                #     self.handle_placement(
                #         pre_line,
                #         obj,
                #         empty_bobj,
                #     )
                #
                # TODO: handle origin things corrrectly...
                # origin_bobj
                # getLinkedObject()
                # >>> doc.Link006.getLinkedObject().Label
                # 'Seagull_Double'
                # >>> doc.Link003.getLinkedObject().Label
                # 'Seagull_A1'
                #
                # if (
                #     not func_data["is_link"]
                # ):
                #     self.handle_placement(
                #         obj,
                #         empty_bobj,
                #     )
                # print(
                #     pre_line +
                #     "'{}' set position"
                #     "".format(empty_bobj)
                #     # "'{}' set position to '{}'"
                #     # "".format(empty_bobj, position)
                # )

        # update func_data links
        func_data["parent_obj"] = obj
        func_data["parent_bobj"] = empty_bobj
        return empty_bobj

    def create_collection_instance(
        self, func_data, pre_line, obj_label, base_collection
    ):
        """Create instance of given collection."""
        result_bobj = bpy.data.objects.new(name=obj_label, object_data=None)
        result_bobj.instance_collection = base_collection
        result_bobj.instance_type = "COLLECTION"
        result_bobj.empty_display_size = self.config["scale"] * 10

        # TODO: CHECK where to add this!
        if func_data["collection"]:
            func_data["collection"].objects.link(result_bobj)
            print(
                pre_line + "'{}' add to '{}' "
                "".format(result_bobj, func_data["collection"])
            )
        # result_bobj.parent = func_data["parent_bobj"]
        # result_bobj.parent = parent_obj
        if result_bobj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(result_bobj)

        return result_bobj

    def create_link_instance(
        self, func_data, pre_line, obj_label, link_target_bobj, link_target_obj
    ):
        """Create instance of given link_target_bobj."""
        result_bobj = None
        if link_target_obj.isDerivedFrom("Part::Feature"):
            object_data = None
            if link_target_bobj:
                object_data = link_target_bobj.data
            else:
                object_data = bpy.data.meshes.new(name=obj_label + ".temp")
            result_bobj = bpy.data.objects.new(name=obj_label, object_data=object_data)
            result_bobj.empty_display_size = self.config["scale"] * 10
        else:
            self.config["report"](
                {"WARNING"},
                ("  TODO: create_link_instance " "part handling not implemented yet!!"),
                pre_line,
            )

        if link_target_bobj:
            result_bobj.scale = link_target_bobj.scale
            # check if we need to create link children...
            if link_target_obj.children:
                self.config["report"](
                    {"WARNING"},
                    (
                        "  Warning: create_link_instance "
                        "children handling not implemented yet!!"
                    ),
                    pre_line,
                )
        return result_bobj

    def handle__sub_object_import(
        self,
        *,
        func_data,
        obj,
        pre_line,
        parent_obj,
        parent_bobj,
        is_link_source=False,
    ):
        """Handle sub object."""
        pre_line_orig = func_data["pre_line"]
        print(pre_line_orig + "handle__sub_object_import")
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line
        link_source = None
        obj_label = self.get_obj_label(obj)
        # print(pre_line + "obj_label:   " + obj_label)
        if func_data["is_link"]:
            obj_label = self.get_sub_obj_label(
                pre_line,
                func_data,
                # parent_obj,
                obj,
            )
            print(
                pre_line
                + "set special link obj_label: "
                + b_helper.colors.fg.green
                + "'{}'".format(obj_label)
                + b_helper.colors.reset
            )
        link_source = func_data["link_source"]
        if is_link_source:
            link_source = obj
        # debug output
        print(pre_line + ("*" * 42))
        print(pre_line + "obj:         " + self.format_obj(obj))
        print(pre_line + "parent_obj:  " + self.format_obj(parent_obj))
        print(pre_line + "parent_bobj:  {}".format(parent_bobj))
        # # print(pre_line + "func_data[is_link]:  {}".format(func_data["is_link"]))
        # is_link_color = b_helper.colors.fg.red
        # if func_data["is_link"]:
        #     is_link_color = b_helper.colors.fg.green
        # print(
        #     pre_line
        #     + "func_data[is_link]: "
        #     + is_link_color
        #     + "{}".format(func_data["is_link"])
        #     + b_helper.colors.reset
        # )
        # is_link_source_color = b_helper.colors.fg.red
        # if is_link_source:
        #     is_link_source_color = b_helper.colors.fg.green
        # print(
        #     pre_line
        #     + "is_link_source: "
        #     + is_link_source_color
        #     + "{}".format(is_link_source)
        #     + b_helper.colors.reset
        # )
        # print(
        #     pre_line
        #     + "func_data[link_source]:  "
        #     + self.format_obj(func_data["link_source"])
        # )
        # print(
        #     pre_line
        #     + "link_source:  "
        #     + self.format_obj(link_source)
        # )
        # print(pre_line + ("*"*42))
        # prepare import
        func_data_new = self.create_func_data()
        func_data_new["obj"] = obj
        func_data_new["obj_label"] = obj_label
        func_data_new["collection"] = func_data["collection"]
        func_data_new["collection_parent"] = func_data["collection_parent"]
        func_data_new["parent_obj"] = parent_obj
        func_data_new["parent_bobj"] = parent_bobj
        func_data_new["is_link"] = func_data["is_link"]
        func_data_new["link_source"] = link_source
        print(pre_line + "import_obj ...")
        self.import_obj(
            func_data=func_data_new, pre_line=pre_line,
        )
        func_data["pre_line"] = pre_line_orig

    def handle__sub_objects(
        self,
        func_data,
        sub_objects,
        pre_line,
        parent_obj,
        parent_bobj,
        include_only_visible=True,
        is_link_source=False,
    ):
        """Handle sub object."""
        # │─ ┌─ └─ ├─ ╞═ ╘═╒═
        # ║═ ╔═ ╚═ ╠═ ╟─
        # ┃━ ┏━ ┗━ ┣━ ┠─
        pre_line_start = pre_line + "╔════ "
        pre_line_sub_special = pre_line + "╠════ "
        pre_line_sub = pre_line + "╠═ "
        pre_line_follow = pre_line + "║   "
        pre_line_end = pre_line + "╚════ "

        pre_line_orig = func_data["pre_line"]
        pre_line = pre_line_follow
        func_data["pre_line"] = pre_line
        print(
            pre_line_start
            + "handle__sub_objects"
            # + " - sub_objects '{}'"
            # + "".format(sub_objects)
        )
        sub_filter_visible = False
        if not isinstance(include_only_visible, list):
            # convert True or False to list
            include_only_visible = [None] * len(sub_objects)
            sub_filter_visible = True
        # print(
        #     pre_line +
        #     "include_only_visible '{}'"
        #     "".format(include_only_visible)
        # )
        # print(
        #     pre_line +
        #     "sub_objects '{}'"
        #     "".format(sub_objects)
        # )
        # print(
        #     pre_line +
        #     "is_link_source '{}'"
        #     "".format(is_link_source)
        # )
        print(pre_line + "parent_obj:  " + self.format_obj(parent_obj))
        print(pre_line + "parent_bobj:  {}".format(parent_bobj))
        sub_objects = fc_helper.filtered_objects(
            sub_objects, include_only_visible=sub_filter_visible
        )
        self.config["report"](
            {"INFO"},
            (
                b_helper.colors.bold
                + b_helper.colors.fg.purple
                + "Import {} Recusive:".format(len(sub_objects))
                + b_helper.colors.reset
            ),
            pre_line=pre_line_sub_special,
        )
        # is_link_source = False
        # # if func_data["is_link"] and len(sub_objects) > 1:
        # if len(sub_objects) > 1:
        #     is_link_source = True
        for index, obj in enumerate(sub_objects):
            if self.check_obj_visibility_with_skiphidden(
                obj, include_only_visible[index]
            ):
                self.print_obj(obj, pre_line_sub)
                self.handle__sub_object_import(
                    func_data=func_data,
                    obj=obj,
                    pre_line=pre_line_follow,
                    parent_obj=parent_obj,
                    parent_bobj=parent_bobj,
                    is_link_source=is_link_source,
                )
            else:
                self.print_obj(
                    obj=obj,
                    pre_line=pre_line_sub,
                    post_line=(
                        b_helper.colors.fg.darkgrey
                        + "  (skipping - hidden)"
                        + b_helper.colors.reset
                    ),
                )
        func_data["pre_line"] = pre_line_orig

        if func_data["bobj"] is None:
            func_data["bobj"] = parent_bobj

        self.config["report"](
            {"INFO"},
            (
                b_helper.colors.bold
                + b_helper.colors.fg.purple
                + "done."
                + b_helper.colors.reset
            ),
            pre_line=pre_line_end,
        )

    def handle__object_with_sub_objects(
        self, func_data, sub_objects, include_only_visible=True, is_link_source=False,
    ):
        """Handle sub objects."""
        pre_line = func_data["pre_line"]
        parent_obj = func_data["obj"]
        parent_label = self.get_obj_label(parent_obj)
        if func_data["is_link"] and func_data["obj_label"]:
            parent_label = func_data["obj_label"]
        print(pre_line + "handle__object_with_sub_objects '{}'".format(parent_label))
        # print(pre_line + "is_link_source '{}'".format(is_link_source))
        # pre_line += "→ "

        # print(pre_line + "force update parent_bobj to match parent_obj")
        # p_label = self.get_obj_label(func_data["parent_obj"])
        # if (
        #     func_data["parent_obj"]
        #     and p_label in bpy.data.objects
        # ):
        #     func_data["parent_bobj"] = bpy.data.objects[p_label]

        self.print_obj(
            func_data["parent_obj"], pre_line=pre_line + "# func_data[parent_obj]",
        )
        print(pre_line + "# func_data[parent_bobj]", func_data["parent_bobj"])

        self.parent_empty_add_or_update(func_data, parent_label)
        parent_bobj = func_data["parent_bobj"]
        print(pre_line + "fresh created parent_bobj ", parent_bobj)

        if len(sub_objects) > 0:
            self.handle__sub_objects(
                func_data,
                sub_objects,
                pre_line,
                parent_obj,
                parent_bobj,
                include_only_visible=include_only_visible,
                is_link_source=is_link_source,
            )
        else:
            self.config["report"](
                {"INFO"},
                (b_helper.colors.fg.darkgrey + "→ no childs." + b_helper.colors.reset),
                pre_line=pre_line,
            )

    # ##########################################
    # Arrays and similar
    def handle__ObjectWithElementList(self, func_data, is_link_source=False):
        """Handle Part::Feature objects."""
        pre_line_orig = func_data["pre_line"]
        print(pre_line_orig + "handle__ObjectWithElementList")
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line
        # fc_helper.print_objects(
        #     func_data["obj"].ElementList,
        #     pre_line=pre_line
        # )
        include_only_visible = [*func_data["obj"].VisibilityList]
        self.handle__object_with_sub_objects(
            func_data,
            func_data["obj"].ElementList,
            include_only_visible=include_only_visible,
            is_link_source=is_link_source,
        )
        func_data["pre_line"] = pre_line_orig

    # Part::FeaturePhython
    def handle__PartFeaturePython_Array(self, func_data):
        """Handle Part::Feature objects."""
        pre_line_orig = func_data["pre_line"]
        print(
            pre_line_orig + "handle__PartFeaturePython_Array",
            self.format_obj(func_data["obj"]),
        )
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line
        pre_line = func_data["pre_line"]
        # print(
        #     pre_line + "ElementList:",
        #     func_data["obj"].ElementList
        # )
        # print(pre_line + "Count:", func_data["obj"].Count)
        # print(pre_line + "ExpandArray:", func_data["obj"].ExpandArray)
        # print(pre_line + "expand Array")
        # TODO: this currently has only any effect in the GUI
        func_data["obj"].ExpandArray = True
        self.doc.recompute()
        # print(pre_line + "ExpandArray:", func_data["obj"].ExpandArray)
        print(pre_line + "ElementList:", func_data["obj"].ElementList)
        # print(
        #     pre_line
        #     + "call handle__ObjectWithElementList with "
        #     + b_helper.colors.fg.orange
        #     + "is_link_source=True"
        #     + b_helper.colors.reset
        #     + ".."
        # )
        self.handle__ObjectWithElementList(func_data, is_link_source=True)
        func_data["pre_line"] = pre_line_orig

    def handle__PartFeaturePython_ArchWithHostChilds(self, func_data):
        """Handle Part::Feature Arch objects with HostsChilds."""
        pre_line_orig = func_data["pre_line"]
        print(
            pre_line_orig + "handle__PartFeaturePython_ArchWithHostChilds",
            self.format_obj(func_data["obj"]),
        )
        pre_line = pre_line_orig + "  "
        func_data["pre_line"] = pre_line
        pre_line = func_data["pre_line"]
        obj = func_data["obj"]
        # import the part itself
        self.handle__PartFeature(func_data)
        # handle childs
        original_parent = func_data["parent_bobj"]
        obj_childs = fc_helper.object_get_HostChilds(obj)
        # print(pre_line + "obj_childs:", obj_childs)
        # print(pre_line + "len(obj_childs):", len(obj_childs))
        self.handle__object_with_sub_objects(func_data, obj_childs)
        # restor
        func_data["parent_bobj"] = original_parent
        func_data["pre_line"] = pre_line_orig

    def handle__PartFeaturePython(self, func_data, pre_line=""):
        """Handle Part::FeaturePython objects."""
        obj = func_data["obj"]
        if hasattr(obj, "ExpandArray") and hasattr(obj, "ElementList"):
            self.handle__PartFeaturePython_Array(func_data)
        elif hasattr(obj, "ArrayType"):
            self.config["report"](
                {"WARNING"},
                (
                    "Unable to load '{}' ('{}') of type '{}'. "
                    "(Type Not implemented yet)."
                    "".format(obj.Label, obj.Name, obj.TypeId)
                ),
                pre_line,
            )
        elif len(fc_helper.object_get_HostChilds(obj)) > 0:
            # Arch Workbench - ArchComponent
            self.handle__PartFeaturePython_ArchWithHostChilds(func_data)
        elif hasattr(obj, "Hosts"):
            # Arch Workbench - Childs
            self.handle__PartFeature(func_data)

            # self.handle__object_hosts(func_data)
            # not needed anymore - as the main import now handles the parent-child relationship
        else:
            self.config["report"](
                {"WARNING"},
                (
                    "try to load '{}' ('{}') of type '{}' as normal Part::Feature. "
                    "no special implementation for Sub-Type of 'Part::FeaturePython' found."
                    "".format(obj.Label, obj.Name, obj.TypeId)
                ),
                pre_line,
            )
            self.handle__PartFeature(func_data)

    # App::Part
    def handle__AppPart(self, func_data):
        """Handle App:Part type."""
        # pre_line = func_data["pre_line"]
        self.handle__object_with_sub_objects(func_data, func_data["obj"].Group)

    # App::Link*
    def add_or_update_collection_instance(
        self, *, func_data, obj, obj_label, instance_target_label,
    ):
        """Add or update collection instance object."""
        pre_line_orig = func_data["pre_line"]
        pre_line = pre_line_orig
        # │─ ┌─ └─ ├─ ╞═ ╘═╒═
        # ║═ ╔═ ╚═ ╠═ ╟─
        # ┃━ ┏━ ┗━ ┣━ ┠─
        pre_line_start = pre_line_orig + "┌ "
        # pre_line_sub = pre_line_orig + "├─ "
        pre_line_follow = pre_line_orig + "│   "
        pre_line_end = pre_line_orig + "└────────── "
        print(
            pre_line_start + "add_or_update_collection_instance '{}'"
            "".format(obj_label)
        )
        func_data["pre_line"] = pre_line_follow
        # pre_line = pre_line_sub
        pre_line = pre_line_follow

        print(pre_line + "obj_label '{}'".format(obj_label))
        print(pre_line + "instance_target_label '{}'".format(instance_target_label))
        print(
            pre_line + "func_data[collection] '{}'" "".format(func_data["collection"])
        )

        base_collection = None
        bobj = None
        if instance_target_label in bpy.data.collections:
            base_collection = bpy.data.collections[instance_target_label]
            flag_new = False
            if obj_label in bpy.data.objects:
                bobj = bpy.data.objects[obj_label]
            else:
                bobj = self.create_collection_instance(
                    func_data, pre_line_follow, obj_label, base_collection
                )
                flag_new = True
            # print(
            #     pre_line +
            #     "bobj '{}'; new:{}"
            #     "".format(bobj, flag_new)
            # )
            if self.config["update"] or flag_new:
                self.set_obj_parent_and_collection(pre_line_follow, func_data, bobj)
                self.handle_placement(pre_line_follow, obj, bobj, enable_scale=True)
                # print(
                #     pre_line + "    "
                #     "bobj '{}' ".format(bobj.location)
                # )
        else:
            self.config["report"](
                {"WARNING"},
                (
                    "Warning: can't add or update instance. "
                    "'{}' collection not found."
                    "".format(instance_target_label)
                ),
                pre_line,
            )
            # return False
        print(pre_line_end + "")
        func_data["pre_line"] = pre_line_orig

    def add_or_update_link_instance(
        self, *, func_data, obj, obj_label, link_target_obj, link_target_label,
    ):
        """Add or update link instance object."""
        pre_line_orig = func_data["pre_line"]
        pre_line = pre_line_orig
        # │─ ┌─ └─ ├─ ╞═ ╘═╒═
        # ║═ ╔═ ╚═ ╠═ ╟─
        # ┃━ ┏━ ┗━ ┣━ ┠─
        pre_line_start = pre_line_orig + "┌ "
        # pre_line_sub = pre_line_orig + "├─ "
        pre_line_follow = pre_line_orig + "│   "
        pre_line_end = pre_line_orig + "└────────── "
        print(pre_line_start + "add_or_update_link_instance '{}'" "".format(obj_label))
        func_data["pre_line"] = pre_line_follow
        # pre_line = pre_line_sub
        pre_line = pre_line_follow

        print(pre_line + "obj_label '{}'".format(obj_label))
        print(pre_line + "link_target_label '{}'".format(link_target_label))

        link_target_bobj = None
        bobj = None
        if link_target_label in bpy.data.objects:
            link_target_bobj = bpy.data.objects[link_target_label]
            print(pre_line + "# link_target_bobj ", link_target_bobj)
        else:
            self.config["report"](
                {"WARNING"},
                (
                    "Warning: can't add or update linnk instance. "
                    "'{}' link_target not found."
                    "".format(link_target_label)
                ),
                pre_line,
            )
            # return False
        flag_new = False
        if obj_label in bpy.data.objects:
            bobj = bpy.data.objects[obj_label]
            print(pre_line + "# bobj already here: ", bobj)
        else:
            bobj = self.create_link_instance(
                func_data, pre_line_follow, obj_label, link_target_bobj, link_target_obj
            )
            print(pre_line + "# created new bobj: ", bobj)
            flag_new = True
        # print(
        #     pre_line +
        #     "bobj '{}'; new:{}"
        #     "".format(bobj, flag_new)
        # )
        if self.config["update"] or flag_new:
            # if func_data["parent_bobj"] is None:
            #     func_data["parent_bobj"] = link_target_bobj
            # print(
            #     pre_line +
            #     "'{}' try to set parent to '{}' "
            #     "".format(bobj, func_data["parent_bobj"])
            # )
            # self.set_obj_parent_and_collection(
            #     pre_line_follow,
            #     func_data,
            #     bobj
            # )
            self.handle_placement(pre_line_follow, obj, bobj, enable_scale=True)
            # print(
            #     pre_line + "    "
            #     "bobj '{}' ".format(bobj.location)
            # )
            print(pre_line + "# bobj.data: ", bobj.data)
            if bobj.data:
                if bobj.data.name != link_target_label:
                    if link_target_label in bpy.data.meshes:
                        print(
                            pre_line
                            + "update / relink '{}' to original link target '{}'"
                            "".format(obj_label, link_target_label)
                        )
                        old_mesh = bobj.data
                        bobj.data = bpy.data.meshes[link_target_label]
                        # clean up temporary mesh
                        if old_mesh.users == 0:
                            bpy.data.meshes.remove(old_mesh)
                    else:
                        print(
                            pre_line + "→ link_target_label not in bpy.data.meshes "
                            "Something wired going on.... "
                            "it seems to working..."
                            "TODO: maybe CHECK"
                        )
                # else:
                #     print(
                #         pre_line +
                #         "→ bobj.data.name '{}' == link_target_label '{}' "
                #         "".format(bobj.data.name, link_target_label)
                #     )
            else:
                print(pre_line + "→ bobj.data == None " "→ maybe this is a Empty.")

            func_data["bobj"] = bobj
            func_data["update_tree"] = True

        print(pre_line_end + "")
        func_data["pre_line"] = pre_line_orig

    def add_or_update_link_target(
        self, *, func_data, obj, obj_label, obj_linkedobj, obj_linkedobj_label,
    ):
        """Add or update link target object."""
        pre_line = func_data["pre_line"]
        # print(
        #     pre_line +
        #     "$ add_or_update_link_target: '{}'"
        #     "".format(
        #         obj_linkedobj_label,
        #     )
        # )
        # print(
        #     pre_line +
        #     "$ obj: '{}' '{}' parent: '{}'"
        #     "".format(
        #         obj,
        #         obj.Label,
        #         obj.getParentGeoFeatureGroup()
        #     )
        # )

        # print(
        #     pre_line +
        #     "self.imported_obj_names ",
        #     self.imported_obj_names
        # )

        if obj_linkedobj_label in bpy.data.objects or (
            obj_linkedobj_label in self.imported_obj_names
        ):
            print(
                pre_line + "→ already imported/updated '{}'."
                "".format(obj_linkedobj_label)
            )
        else:
            self.print_obj(
                obj,
                pre_line=pre_line + "# ",
                post_line=" → import Link Target {}.".format(
                    self.format_obj(obj_linkedobj)
                ),
                end="",
            )

            # self.print_obj(
            #     obj_linkedobj,
            #     pre_line=pre_line + "# ",
            #     post_line=""
            # )

            # self.print_obj(
            #     func_data["parent_obj"],
            #     pre_line=pre_line + "# func_data[parent_obj]",
            # )
            # print(
            #     pre_line + "# func_data[parent_bobj]",
            #     func_data["parent_bobj"]
            # )

            # if obj_linkedobj_label in bpy.data.objects:
            #     self.config["report"]({'INFO'}, (
            #         "skipping import. '{}' already in objects list."
            #         "".format(obj_linkedobj_label)
            #     ), pre_line)
            # else:
            # set collection to link_target
            # this way the imports get definitly added to the scene.
            # func_data["collection"] = self.link_targets
            print(pre_line + "§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§")
            func_data_obj_linked = self.create_func_data()
            func_data_obj_linked["obj"] = obj_linkedobj
            func_data_obj_linked["collection"] = self.link_targets
            func_data_obj_linked["collection_parent"] = None
            func_data_obj_linked["parent_obj"] = obj
            func_data_obj_linked["parent_bobj"] = None
            func_data_obj_linked = self.import_obj(
                func_data=func_data_obj_linked, pre_line=pre_line + "    ",
            )
            print(pre_line + "§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§")
            bobj = func_data_obj_linked["bobj"]
            # print(
            #    pre_line +
            #    "func_data_obj_linked '{}' "
            #    "".format(func_data_obj_linked)
            # )
            # pprint.pprint(func_data_obj_linked)

            # fix parent linking
            # parent_obj = obj_linked.getParentGeoFeatureGroup()
            # parent_label = self.get_obj_label(parent_obj)
            # if parent_label:
            #     parent_bobj = bpy.data.objects[parent_label]
            #     if parent_bobj:
            #         bobj.parent = parent_bobj
            #         print(
            #             pre_line +
            #             "'{}' set parent to '{}' "
            #             "".format(bobj, parent_bobj)
            #         )
            # this has no parent as we use only the raw obj.
            self.print_obj(func_data_obj_linked["obj"], pre_line + "$ used obj: ")
            print(pre_line + "$ created bobj: ", bobj)
            print(pre_line + "$ bobj.parent: ", bobj.parent)
            print(pre_line + "$ func_data[parent_bobj]: ", func_data["parent_bobj"])
            # bobj.parent = None
            self.reset_placement_position(bobj)

            # print(
            #     pre_line + "$ parent_bobj: ",
            #     func_data_obj_linked["parent_bobj"]
            # )
            # print(
            #     pre_line + "$ collection: ",
            #     func_data_obj_linked["collection"]
            # )
            # print(
            #     pre_line + "$ collection_parent: ",
            #     func_data_obj_linked["collection_parent"]
            # )

            # created collection for new link target
            func_data_obj_linked["collection"] = self.link_targets
            self.sub_collection_add_or_update(func_data_obj_linked, obj_linkedobj_label)
            # self.parent_empty_add_or_update(
            #     func_data_obj_linked, obj_linkedobj_label)
            # add new object to collection.
            func_data_obj_linked["collection"].objects.link(bobj)
            print(
                pre_line + "'{}' add to '{}' "
                "".format(bobj, func_data_obj_linked["collection"])
            )

    def handle__AppLink(self, func_data):
        """Handle App::Link objects."""
        pre_line_orig = func_data["pre_line"]
        pre_line = pre_line_orig
        # │─ ┌─ └─ ├─ ╞═ ╘═╒═
        # ║═ ╔═ ╚═ ╠═ ╟─
        # ┃━ ┏━ ┗━ ┣━ ┠─
        pre_line_start = pre_line_orig + "┌ "
        # pre_line_sub = pre_line_orig + "├─ "
        pre_line_follow = pre_line_orig + "│   "
        pre_line_end = pre_line_orig + "└────────── "
        print(pre_line_start + "handle__AppLink")
        func_data["pre_line"] = pre_line_follow
        # pre_line = pre_line_sub
        pre_line = pre_line_follow

        obj = func_data["obj"]
        obj_linkedobj = func_data["obj"].LinkedObject
        if isinstance(obj_linkedobj, tuple):
            obj_linkedobj = obj_linkedobj[0]
        # print(pre_line + "obj_linkedobj :", obj_linkedobj)
        # self.config["report"]({'WARNING'}, (
        #     "'{}' ('{s}') of type '{}': "
        #     "".format(obj.Label, obj.Name, obj.TypeId)
        # ), pre_line)
        # self.config["report"]({'WARNING'}, (
        #     "  Warning: App::Link handling is highly experimental!!"
        # ), pre_line)
        obj_label = self.get_obj_label(obj)
        if func_data["is_link"] and func_data["obj_label"]:
            obj_label = func_data["obj_label"]
        # obj_linkedobj_label = self.get_obj_linkedobj_label(obj)
        # obj_linked_label = self.get_obj_label(obj_linkedobj)

        # print(pre_line + "obj_label:", obj_label)
        # print(pre_line + "obj_linkedobj_label:", obj_linkedobj_label)
        # print(pre_line + "obj_linked_label:", obj_linked_label)
        # fc_helper.print_obj(
        #     obj,
        #     pre_line=pre_line + "obj          : ")
        # fc_helper.print_obj(
        #     obj_linkedobj,
        #     pre_line=pre_line + "obj_linkedobj: ")
        # if hasattr(obj_linkedobj, "LinkedObject"):
        #     fc_helper.print_obj(obj_linkedobj.LinkedObject, pre_line=pre_line)

        if obj_linkedobj:
            orig_is_link = func_data["is_link"]
            func_data["is_link"] = True

            if hasattr(obj, "ElementList") and len(obj.ElementList) > 0:
                print(pre_line + "ElementList > 0")
                self.handle__ObjectWithElementList(func_data)
            else:
                print(pre_line + "Single Element → fake list")
                # if target is of Body type get real link target
                # this excludes the link → link → link chain...
                # try:
                #     obj_linkedobj.getLinkedObject().isDerivedFrom("Part::Feature")
                # except Exception as e:
                #     print(pre_line + "obj_linkedobj error:", e)
                # else:
                #     print(pre_line + "use recusive inner target")
                #     obj_linkedobj = obj_linkedobj.getLinkedObject()
                if obj_linkedobj.getLinkedObject().isDerivedFrom("Part::Feature"):
                    print(pre_line + "use recusive inner target")
                    obj_linkedobj = obj_linkedobj.getLinkedObject()
                self.handle__object_with_sub_objects(
                    func_data, [obj_linkedobj], include_only_visible=[True]
                )
            # set back to original
            func_data["is_link"] = orig_is_link
        else:
            self.config["report"](
                {"WARNING"},
                ("Warning: '{}' LinkedObject is NONE → skipping." "".format(obj_label)),
                pre_line,
            )
        print(pre_line_end + "")
        func_data["pre_line"] = pre_line_orig

    def handle__AppLinkElement(self, func_data, obj_linkedobj=None):
        """Handle App::LinkElement objects."""
        pre_line_orig = func_data["pre_line"]

        pre_line = pre_line_orig
        # │─ ┌─ └─ ├─ ╞═ ╘═╒═
        # ║═ ╔═ ╚═ ╠═ ╟─
        # ┃━ ┏━ ┗━ ┣━ ┠─
        pre_line_start = pre_line_orig + "┌ "
        # pre_line_sub = pre_line_orig + "├─ "
        pre_line_follow = pre_line_orig + "│   "
        pre_line_end = pre_line_orig + "└────────── "
        print(pre_line_start + "handle__AppLinkElement")
        func_data["pre_line"] = pre_line_follow
        # pre_line = pre_line_sub
        pre_line = pre_line_follow

        obj = func_data["obj"]
        if obj_linkedobj is None:
            obj_linkedobj = func_data["obj"].LinkedObject

        # if hasattr(obj_linkedobj, "LinkedObject"):
        #     # if we have Arrays they  have a intermediet link object..
        #     # we skip this..
        #     obj_linkedobj = obj_linkedobj.LinkedObject

        # parent_obj = obj.InList[0]
        parent_obj = func_data["parent_obj"]
        # parent_obj_label = self.get_obj_label(parent_obj)
        # if (
        #     parent_obj and
        #     parent_obj_label in bpy.data.objects
        # ):
        #     func_data["parent_bobj"] = bpy.data.objects[parent_obj_label]
        print(pre_line + "func_data[parent_bobj]:", func_data["parent_bobj"])

        # obj_label = self.get_obj_combined_label(parent_obj, obj)
        obj_label = self.get_obj_label(obj)
        if func_data["is_link"] and func_data["obj_label"]:
            obj_label = func_data["obj_label"]
        # obj_linkedobj_label = self.get_obj_linkedobj_label(obj)
        obj_linkedobj_label = self.get_obj_label(obj_linkedobj)

        # print(pre_line + "collection:", func_data["collection"])
        # print(pre_line + "parent_obj_label:", parent_obj_label)
        print(pre_line + "obj_label:", obj_label)
        print(pre_line + "obj_linkedobj_label:", obj_linkedobj_label)
        fc_helper.print_obj(parent_obj, pre_line=pre_line + "parent_obj   : ")
        fc_helper.print_obj(obj, pre_line=pre_line + "obj          : ")
        fc_helper.print_obj(obj_linkedobj, pre_line=pre_line + "obj_linkedobj: ")
        # fc_helper.print_obj(obj_linked.LinkedObject, pre_line=pre_line)

        if not self.config["links_as_collectioninstance"]:
            self.add_or_update_link_instance(
                func_data=func_data,
                obj=obj,
                obj_label=obj_label,
                link_target_obj=obj_linkedobj,
                link_target_label=obj_linkedobj_label,
            )

        self.add_or_update_link_target(
            func_data=func_data,
            obj=obj,
            obj_label=obj_label,
            obj_linkedobj=obj_linkedobj,
            obj_linkedobj_label=obj_linkedobj_label,
        )

        if self.config["links_as_collectioninstance"]:
            self.add_or_update_collection_instance(
                func_data=func_data,
                obj=obj,
                obj_label=obj_label,
                instance_target_label=obj_linkedobj_label,
            )
        else:
            self.add_or_update_link_instance(
                func_data=func_data,
                obj=obj,
                obj_label=obj_label,
                link_target_obj=obj_linkedobj,
                link_target_label=obj_linkedobj_label,
            )
        print(pre_line_end + "")
        func_data["pre_line"] = pre_line_orig

    # ##########################################
    # 'Arch' object types
    def handle__object_hosts(self, func_data):
        """Handle object with hosts attribute (Arch Workbench)."""
        pre_line = func_data["pre_line"]
        obj = func_data["obj"]
        obj_host = obj.Hosts[0]
        obj_label = self.get_obj_label(obj)
        obj_host_label = self.get_obj_label(obj_host)
        print(pre_line + "handle__object_hosts '{}'".format(obj_label))
        print(pre_line + "obj_host_label '{}'".format(obj_host_label))
        bobj = func_data["bobj"]
        bobj_host = bpy.data.objects[obj_host_label]
        if bobj_host:
            print(pre_line + "bobj_host '{}'".format(bobj_host))
            print(pre_line + "bobj_host.parent '{}'".format(bobj_host.parent))
            # Arch Wall Objects are no collection things - so we need to use the parent of it...
            # in the hope that this works...
            if bobj_host.parent:
                bobj.parent = bobj_host.parent
            else:
                self.config["report"](
                    {"WARNING"},
                    (
                        "Warning: host '{}' has no parrent. can not set parent for '{}' "
                        "".format(obj_host_label, obj_label)
                    ),
                    pre_line,
                )

    # ##########################################
    # 'real' object types

    # Part::Feature
    def handle_shape_edge(self, func_data, edge):
        """Handle edges that are not part of a face."""
        if self.hascurves(edge):
            # TODO use tessellation value
            dv = edge.discretize(9)
            for i in range(len(dv) - 1):
                dv1 = [dv[i].x, dv[i].y, dv[i].z]
                dv2 = [dv[i + 1].x, dv[i + 1].y, dv[i + 1].z]
                if dv1 not in func_data["verts"]:
                    func_data["verts"].append(dv1)
                if dv2 not in func_data["verts"]:
                    func_data["verts"].append(dv2)
                func_data["edges"].append(
                    [func_data["verts"].index(dv1), func_data["verts"].index(dv2)]
                )
        else:
            e = []
            for vert in edge.Vertexes:
                # TODO discretize non-linear edges
                v = [vert.X, vert.Y, vert.Z]
                if v not in func_data["verts"]:
                    func_data["verts"].append(v)
                e.append(func_data["verts"].index(v))
            func_data["edges"].append(e)

    def convert_face_to_polygon(self, func_data, face, faceedges):
        """Convert face to polygons."""
        import Part

        if (
            (len(face.Wires) > 1)
            or (not isinstance(face.Surface, Part.Plane))
            or self.hascurves(face)
        ):
            # face has holes or is curved, so we need to triangulate it
            rawdata = face.tessellate(self.config["tessellation"])
            for v in rawdata[0]:
                vl = [v.x, v.y, v.z]
                if vl not in func_data["verts"]:
                    func_data["verts"].append(vl)
            for f in rawdata[1]:
                nf = []
                for vi in f:
                    nv = rawdata[0][vi]
                    nf.append(func_data["verts"].index([nv.x, nv.y, nv.z]))
                func_data["faces"].append(nf)
            func_data["matindex"].append(len(rawdata[1]))
        else:
            f = []
            ov = face.OuterWire.OrderedVertexes
            for v in ov:
                vl = [v.X, v.Y, v.Z]
                if vl not in func_data["verts"]:
                    func_data["verts"].append(vl)
                f.append(func_data["verts"].index(vl))
            # FreeCAD doesn't care about func_data["verts"] order.
            # Make sure our loop goes clockwise
            c = face.CenterOfMass
            v1 = ov[0].Point.sub(c)
            v2 = ov[1].Point.sub(c)
            n = face.normalAt(0, 0)
            if (v1.cross(v2)).getAngle(n) > 1.57:
                # inverting func_data["verts"] order
                # if the direction is counterclockwise
                f.reverse()
            func_data["faces"].append(f)
            func_data["matindex"].append(1)
        for e in face.Edges:
            faceedges.append(e.hashCode())

    def handle_shape_faces(self, func_data, shape, faceedges):
        """Convert faces to polygons."""
        if self.config["triangulate_meshes"]:
            # triangulate and make faces
            rawdata = shape.tessellate(self.config["tessellation"])
            for v in rawdata[0]:
                func_data["verts"].append([v.x, v.y, v.z])
            for f in rawdata[1]:
                func_data["faces"].append(f)
            for face in shape.Faces:
                for e in face.Edges:
                    faceedges.append(e.hashCode())
        else:
            # write FreeCAD faces as polygons when possible
            for face in shape.Faces:
                self.convert_face_to_polygon(func_data, face, faceedges)

    def create_mesh_from_shape(self, func_data):
        """Create mesh from shape."""
        # print(func_data["pre_line"] + "create_mesh_from_shape")
        # a placeholder to store edges that belong to a face
        faceedges = []
        shape = func_data["obj"].Shape
        # func_data["freecad_mesh_hash"] = shape.hashCode()
        # hashCode changes on every file opening :-(
        if self.config["placement"]:
            shape = func_data["obj"].Shape.copy()
            shape.Placement = (
                func_data["obj"].Placement.inverse().multiply(shape.Placement)
            )
        if shape.Faces:
            self.handle_shape_faces(func_data, shape, faceedges)
        # Treat remaining edges (that are not in faces)
        for edge in shape.Edges:
            if not (edge.hashCode() in faceedges):
                self.handle_shape_edge(func_data, edge)
        return shape

    def handle__PartFeature(self, func_data):
        """Handle Part::Feature objects."""
        pre_line_orig = func_data["pre_line"]
        pre_line = func_data["pre_line"]
        print(func_data["pre_line"] + "handle__PartFeature")
        pre_line += "> "
        func_data["pre_line"] = pre_line

        obj = func_data["obj"]
        obj_label = self.get_obj_label(obj)
        if func_data["is_link"] and func_data["obj_label"]:
            obj_label = func_data["obj_label"]

        # import_it = False
        update_placement = False
        # check if this Part::Feature object is already imported.
        if self.config["links_as_collectioninstance"]:
            if (
                obj_label in self.link_targets.children
                and obj_label in bpy.data.objects
            ):
                # print(
                #     pre_line + "found link target object '{}'"
                #     "".format(obj_label)
                # )
                bobj_link_target = bpy.data.objects[obj_label]
                # bobj_link_target_label = self.fix_link_target_name(
                self.fix_link_target_name(bobj_link_target)
                # print(
                #     pre_line + "fixed name. '{}'"
                #     "".format(bobj_link_target)
                # )
                # self.add_or_update_link_target(
                #     func_data=func_data,
                #     obj=obj,
                #     obj_linked=obj_linkedobj,
                #     obj_linkedobj_label=bobj_link_target_label,
                # )
                self.add_or_update_collection_instance(
                    func_data=func_data,
                    obj=obj,
                    obj_label=obj_label,
                    # instance_target_label=bobj_link_target_label,
                    instance_target_label=obj_label,
                )
            else:
                # import_it = True
                pass
        else:
            # handle creation of linked copies
            print(pre_line + "handle creation of linked copies..")
            # print(pre_line + "imported_obj_names:", self.imported_obj_names)
            if (
                obj_label
                in bpy.data.objects
                # and obj_label in self.imported_obj_names
            ):
                print(pre_line + "→ update bobj")
                bobj = bpy.data.objects[obj_label]
                func_data["bobj"] = bobj
                if not func_data["is_link"]:
                    update_placement = True
                func_data["update_tree"] = True
            else:
                print(pre_line + "→ just import it")
                # import_it = True

        # if import_it:
        self.create_mesh_from_shape(func_data)
        if func_data["verts"] and (func_data["faces"] or func_data["edges"]):
            self.add_or_update_blender_obj(func_data)
            func_data["update_tree"] = True

        if update_placement:
            # print(pre_line + "update_placement..")
            self.handle_placement(
                pre_line, obj, func_data["bobj"],
            )

        # restore
        func_data["pre_line"] = pre_line_orig

    # Mesh::Feature
    def handle__MeshFeature(self, func_data):
        """Convert freecad mesh to blender mesh."""
        mesh = func_data["obj"].Mesh
        if self.config["placement"]:
            # in meshes, this zeroes the placement
            mesh = func_data["obj"].Mesh.copy()
        t = mesh.Topology
        func_data["verts"] = [[v.x, v.y, v.z] for v in t[0]]
        func_data["faces"] = t[1]

    # ##########################################
    # main object import
    def create_func_data(self):
        "Create a blank func_data structure."
        func_data = {
            "obj": None,
            "bobj": None,
            "obj_label": None,
            "verts": [],
            "edges": [],
            "faces": [],
            "freecad_mesh_hash": None,
            # face to material relationship
            "matindex": [],
            # to store reusable materials
            "matdatabase": {},
            # name: "Unnamed",
            "link_targets": [],
            "collection": None,
            "collection_parent": None,
            "parent_obj": None,
            "parent_bobj": None,
            "pre_line": "",
            "update_tree": False,
            "is_link": False,
            "link_source": None,
        }
        return func_data

    def _import_obj__handle_type(self, func_data, pre_line=""):
        """Choose Import Type."""
        obj = func_data["obj"]
        if obj.isDerivedFrom("Part::FeaturePython"):
            self.handle__PartFeaturePython(func_data, pre_line)
        elif obj.isDerivedFrom("Part::Feature"):
            self.handle__PartFeature(func_data)
        elif obj.isDerivedFrom("Mesh::Feature"):
            self.handle__MeshFeature(func_data)
        # elif obj.isDerivedFrom("PartDesign::Body"):
        #     self.create_mesh_from_Body(func_data)
        # elif obj.isDerivedFrom("XXXXXX"):
        #     self.handle__XXXXXX(func_data)
        elif obj.isDerivedFrom("App::Part"):
            self.handle__AppPart(func_data)
        elif obj.isDerivedFrom("App::LinkElement"):
            # self.handle__AppLinkElement(func_data)
            self.handle__AppLink(func_data)
        elif obj.isDerivedFrom("App::Link"):
            self.handle__AppLink(func_data)
        else:
            self.config["report"](
                {"WARNING"},
                (
                    "Unable to load '{}' ('{}') of type '{}'. "
                    "(Type Not implemented yet)."
                    "".format(obj.Label, obj.Name, obj.TypeId)
                ),
                pre_line,
            )
        return func_data

    def import_obj(
        self,
        func_data=None,
        # obj=None,
        # collection=None,
        # collection_parent=None,
        # parent_obj=None,
        # parent_bobj=None,
        pre_line="",
    ):
        """Import Object."""
        # import some FreeCAD modules needed below.
        # After "import FreeCAD" these modules become available
        # import Part
        # import PartDesign
        # print("import_obj: obj", obj)
        # dict for storing all data
        if not func_data:
            func_data = self.create_func_data()
        func_data["pre_line"] = pre_line
        obj = func_data["obj"]
        if obj:
            self._import_obj__handle_type(func_data, pre_line)

            if func_data["update_tree"]:
                self.update_tree_collections(func_data)
                self.update_tree_parents(func_data)
        return func_data

    def import_doc_content(self, doc):
        """Import document content = filterd objects."""
        pre_line = ""
        obj_list, obj_list_withHost = fc_helper.get_root_objects(
            doc, filter_list=self.typeid_filter_list
        )
        print("-" * 21)

        self.config["report"](
            {"INFO"},
            (
                "found {} root objects in '{}'"
                "".format(len(obj_list), self.doc_filename)
            ),
            pre_line=pre_line,
        )
        fc_helper.print_objects(obj_list, show_lists=True, show_list_details=True)
        print("-" * 21)

        self.config["report"](
            {"INFO"},
            (
                "found {} objects with Hosts attribute set in '{}' - will be handled as childs.."
                "".format(len(obj_list_withHost), self.doc_filename)
            ),
            pre_line=pre_line,
        )
        fc_helper.print_objects(
            obj_list_withHost, show_lists=True, show_list_details=True
        )
        print("-" * 21)
        # self.config["report"](
        #     {"INFO"},
        #     ("the Hosts ARCH way is not implemented yet. so we just import them."),
        #     pre_line=pre_line,
        # )
        # obj_list.extend(obj_list_withHost)
        # fc_helper.print_objects(obj_list, show_lists=True)
        # print("-" * 21)

        # │─ ┌─ └─ ├─ ╞═ ╘═╒═
        # ║═ ╔═ ╚═ ╠═ ╟─
        # ┃━ ┏━ ┗━ ┣━ ┠─
        pre_line_start = pre_line + "┏━━━━ "
        pre_line_sub = pre_line + "┣━ "
        pre_line_follow = pre_line + "┃    "
        pre_line_end = pre_line + "┗━━━━ "
        self.config["report"]({"INFO"}, "Import", pre_line=pre_line_start)
        for obj in obj_list:
            if self.check_obj_visibility_with_skiphidden(obj):
                self.print_obj(obj, pre_line=pre_line_sub)
                func_data_new = self.create_func_data()
                func_data_new["obj"] = obj
                func_data_new["collection"] = self.fcstd_collection
                func_data_new["parent_bobj"] = self.fcstd_empty
                self.import_obj(
                    func_data=func_data_new, pre_line=pre_line_follow,
                )
                if obj in obj_list_withHost:
                    self.config["report"](
                        {"INFO"},
                        ("TODO: handle Hosts [{}] of obj '{}'").format(obj.Hosts, obj),
                        pre_line=pre_line_follow,
                    )
            else:
                self.print_obj(
                    obj=obj,
                    pre_line=pre_line_sub,
                    post_line=(
                        b_helper.colors.fg.darkgrey
                        + "  (skipping - hidden)"
                        + b_helper.colors.reset
                    ),
                )
        self.config["report"]({"INFO"}, "finished.", pre_line=pre_line_end)

    def prepare_collection(self):
        """Prepare main import collection."""
        link_targets_label = self.doc.Name + "__link_targets"
        if self.config["update"]:
            if self.doc_filename in bpy.data.collections:
                self.fcstd_collection = bpy.data.collections[self.doc_filename]
            if link_targets_label in bpy.data.collections:
                self.link_targets = bpy.data.collections[link_targets_label]

        if not self.fcstd_collection:
            self.fcstd_collection = bpy.data.collections.new(self.doc_filename)
            bpy.context.scene.collection.children.link(self.fcstd_collection)

        if not self.link_targets:
            self.link_targets = bpy.data.collections.new(link_targets_label)
            self.fcstd_collection.children.link(self.link_targets)
            # hide this internal object.
            # we use only the instances..
            self.link_targets.hide_render = False
            self.link_targets.hide_select = True
            self.link_targets.hide_viewport = False
            # exclude from all view layers
            for lc in helper.find_layer_collection_in_scene(
                collection_name=link_targets_label
            ):
                lc.exclude = True

    def prepare_root_empty(self):
        """Prepare import file root empty."""
        func_data = {
            "obj": None,
            "parent_obj": None,
            "parent_bobj": None,
            "collection": self.fcstd_collection,
            "pre_line": "",
        }
        self.fcstd_empty = self.parent_empty_add_or_update(func_data, self.doc_filename)

    def append_path(self, path, sub=""):
        if path and sub:
            path = os.path.join(path, sub)
            print("full path:", path)
        if path and os.path.exists(path):
            if os.path.isfile(path):
                path = os.path.dirname(path)
            print("configured path:", path)
            if path not in sys.path:
                sys.path.append(path)
        else:
            self.config["report"](
                {"WARNING"}, ("Path does not exist. Please check! " "'{}'".format(path))
            )

    def prepare_freecad_path(self):
        """Find FreeCAD libraries."""
        # https://github.com/s-light/io_import_fcstd/issues/11  (original repo, now rebranded as FreeBImport_v01)

        # check user specified location specified in addon preferences

        # try snap
        # "/snap/freecad/current/usr/lib/"

        # try appimage 
        self.appimage_mounted = False
        # my.AppImage --appimage-mount
        # use mountingpoitn.

        # try flatpack

        # set path to new location
        # self.path_to_freecad
        # self.path_to_system_packages

    def prepare_freecad_import(self):
        """Prepare FreeCAD import."""
        self.append_path(self.path_to_freecad)
        self.append_path(self.path_to_system_packages)
    
    def cleanup_freecad_import(self):
        """Cleanup if nessesary."""
        if self.appimage_mounted:
            pass


    def handle_additonal_paths(self):
        """Prepare more paths for import."""
        import FreeCAD

        path_base = FreeCAD.getResourceDir()  # noqa
        # https://wiki.freecadweb.org/PySide
        # /usr/share/freecad-daily/Ext/PySide
        self.append_path(path_base, "Ext")
        self.append_path(path_base, "Mod")

    def import_extras(self):
        """Import additional things."""
        self.handle_additonal_paths()
        try:
            import Part  # noqa

            # import PartDesign  # noqa
            import Draft  # noqa
            import Arch  # noqa
        except ModuleNotFoundError as e:
            self.config["report"](
                {"ERROR"},
                "Unable to import one of the additional modules. \n"
                "\n"
                "Make sure it can be found by Python, \n"
                "you might need to set its path in this Addon preferences.. "
                "(User preferences->Addons->expand this addon).\n"
                "\n" + str(e),
            )
            return {"CANCELLED"}
        except Exception as e:
            self.config["report"]({"ERROR"}, "Import Failed.\n" "\n" + str(e))
            return {"CANCELLED"}

    def apply_auto_smooth(self):
        """Apply auto smooth using Blender's built-in functionality."""
        if not self.config["auto_smooth_use"]:
            return
            
        print("Applying auto smooth to imported objects...")
        
        try:
            # Apply auto smooth to all imported mesh objects
            mesh_count = 0
            for obj_name in self.imported_obj_names:
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    if obj.type == 'MESH' and hasattr(obj.data, "use_auto_smooth"):
                        # Enable auto smooth (this is the "shade auto smooth" functionality)
                        obj.data.use_auto_smooth = True
                        obj.data.auto_smooth_angle = self.config["auto_smooth_angle"]
                        mesh_count += 1
                
            print(f"Auto smooth applied to {mesh_count} mesh objects with angle {math.degrees(self.config['auto_smooth_angle'])}°")
                
        except Exception as e:
            print(f"Error during auto smooth application: {e}")

    def cleanup_meshes(self):
        """Clean up imported meshes using Blender's built-in operators."""
        if not self.config["cleanup_after_import"]:
            return
            
        print("Cleaning up imported meshes...")
        
        try:
            # Select all imported mesh objects
            mesh_objects = []
            for obj_name in self.imported_obj_names:
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    if obj.type == 'MESH':
                        mesh_objects.append(obj)
            
            if not mesh_objects:
                print("No mesh objects found to clean up.")
                return
            
            # Deselect all objects first
            bpy.ops.object.select_all(action='DESELECT')
            
            # Select all imported mesh objects
            for obj in mesh_objects:
                obj.select_set(True)
            
            # Set the active object (required for operations)
            if mesh_objects:
                bpy.context.view_layer.objects.active = mesh_objects[0]
            
            # Enter edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Select all faces
            bpy.ops.mesh.select_all(action='SELECT')
            
            # Apply Tris to Quads
            print("Applying Tris to Quads...")
            bpy.ops.mesh.tris_convert_to_quads()
            
            # Apply Limited Dissolve
            print("Applying Limited Dissolve...")
            bpy.ops.mesh.dissolve_limited()
            
            # Return to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            print(f"Cleanup completed on {len(mesh_objects)} mesh objects")
                
        except Exception as e:
            print(f"Error during mesh cleanup: {e}")
            # Make sure we return to object mode if there was an error
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
        finally:
            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')

    def import_fcstd(self, filename=None):
        """Read a FreeCAD .FCStd file and creates Blender objects."""
        if filename:
            self.config["filename"] = filename

        try:
            self.prepare_freecad_path()
            self.prepare_freecad_import()
            import FreeCAD
        except ModuleNotFoundError as e:
            self.config["report"](
                {"ERROR"},
                "Unable to import the FreeCAD Python module. \n"
                "\n"
                "Make sure FreeCAD is installed on your system! \n"
                "and compiled with Python3 (same version as Blender).\n"
                "We tried to search for it - \n"
                "but maybee its easier to set its path in this Addon preferences "
                "(User preferences->Addons->expand this addon).\n"
                "\n" + str(e),
            )
            return {"CANCELLED"}
        except Exception as e:
            self.config["report"]({"ERROR"}, "Import Failed.\n" "\n" + str(e))
            return {"CANCELLED"}
        finally:
            self.cleanup_freecad_import()

        self.import_extras()

        self.guidata = guidata.load_guidata(
            self.config["filename"], self.config["report"],
        )

        # Context Managers not implemented..
        # see https://docs.python.org/3.8/reference/compound_stmts.html#with
        # with FreeCAD.open(self.config["filename"]) as doc:
        # so we use the classic try finally block:
        try:
            # doc = FreeCAD.open(
            #     "/home/stefan/mydata/freecad/tests/linking_test/Linking.FCStd")
            self.config["report"](
                {"INFO"}, "open FreeCAD file. '{}'" "".format(self.config["filename"])
            )
            try:
                doc = FreeCAD.open(self.config["filename"])
            except Exception as e:
                print(e)
            docname = doc.Name
            if doc:
                self.doc_filename = doc.Name + ".FCStd"
                self.config["report"](
                    {"INFO"},
                    "File '{}' successfully opened." "".format(self.doc_filename),
                )
                self.doc = doc
                # self.print_debug_report()
                self.config["report"]({"INFO"}, "recompute..")
                self.doc.recompute()
                # self.config["report"]({'INFO'}, "importLinks..")
                # self.doc.importLinks()
                # importLinks is currently not reliable..
                # self.config["report"]({'INFO'}, "recompute..")
                # self.doc.recompute()
                self.prepare_collection()
                self.prepare_root_empty()
                self.import_doc_content(doc)
            else:
                self.config["report"](
                    {"ERROR"},
                    "Unable to open the given FreeCAD file '{}'"
                    "".format(self.config["filename"]),
                )
                return {"CANCELLED"}
        except Exception as e:
            self.config["report"]({"ERROR"}, str(e))
            raise e
        finally:
            FreeCAD.closeDocument(docname)
        
        # Apply auto smooth if requested
        self.apply_auto_smooth()
        
        # Clean up meshes
        self.cleanup_meshes()
        
        print("Import finished.")
        return {"FINISHED"}


def main_test():
    """Tests."""
    pass


if __name__ == "__main__":
    main_test()
