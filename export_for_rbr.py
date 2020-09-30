#TODO detect impossible splitting and enlarge the max_distance in each iteration, then give up
#TODO try different axis before giving up the slicing
#TODO display status messages in the panel
#TODO overall refactoring
#TODO remember and display recent directories for export
#TODO add scenery to the mesh type selection

bl_info = {
    "name": "Export X for RBR",
    "category": "Object",
    "location": "Properties -> Object"
}
import bpy
import bmesh
import time
import os
from mathutils import Vector
from math import radians

from bpy.props import (StringProperty,
                         BoolProperty,
                         IntProperty,
                         FloatProperty,
                         FloatVectorProperty,
                         EnumProperty,
                         PointerProperty,
                         )
from bpy.types import (Panel,
                         Operator,
                         AddonPreferences,
                         PropertyGroup,
                         )
from bpy.app.handlers import persistent

SCENERY_MAX_VERTICES = 7000
SCENERY_MAX_VERTICES_X = 7000
SCENERY_MAX_LENGTH = 0

GENERAL_MAX_VERTICES = 25000
GENERAL_MAX_VERTICES_X = 400000
GENERAL_MAX_LENGTH = 300

class SplitAndExport(bpy.types.Operator):

    bl_idname = "object.split_export_rbr"
    bl_label = "Split & Export X"
    bl_description = "Split & Export selected objects to DirectX files"
    bl_options = {'REGISTER', 'UNDO'}
    
    props = None

    
    def execute(self, context):
 
        self.props = context.scene.export_for_rbr_props
        
        eval("self.props.export_basename_" + self.props.export_mesh_type).strip()
        if eval("self.props.export_basename_" + self.props.export_mesh_type) == "":
            self.report({'ERROR'}, "Enter the name for the exported file")
            return {'CANCELLED'}
            
        if Split.execute(self, context) == {'FINISHED'}:
            if ExportX.execute(self, context) == {'FINISHED'}:
                return {'FINISHED'}
        return {'CANCELLED'}


class ExportX(bpy.types.Operator):

    bl_idname = "object.export_x_rbr"
    bl_label = "Export X"
    bl_description = "Export selected objects to DirectX files"
    bl_options = {'REGISTER', 'UNDO'}

    files_exported = 0
    objects_to_export = None
    props = None
    
    def execute(self, context):

        self.props = context.scene.export_for_rbr_props
        self.objects_to_export = context.selected_objects
        self.files_exported = 0

        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "No object selected!")
            return {'CANCELLED'}
       
        # no modifiers allowed
        for obj in context.selected_objects:
            if len(obj.modifiers) > 0:
                self.report({'ERROR'}, "Apply modifiers first")
                return {'CANCELLED'}
                
        eval("self.props.export_basename_" + self.props.export_mesh_type).strip()
        if eval("self.props.export_basename_" + self.props.export_mesh_type) == "":
            self.report({'ERROR'}, "Enter the name for the exported file")
            return {'CANCELLED'}
            
        print( "\nEXPORTING TO X")
        print( "=====================\n")

        
        def getView3D():
            areas = {}                                                               
            count = 0
            for area in bpy.context.screen.areas:                                  
                areas[area.type] = count                                             
                count += 1

            return bpy.context.screen.areas[areas['VIEW_3D']].spaces[0]
        
        
        def exportChunks():

            vertex_count = 0

            bpy.ops.object.select_all(action="DESELECT")

            for obj in self.objects_to_export:
                vertex_count += len(obj.data.vertices)
                
                if self.props.export_mesh_type == "scenery":
                    if vertex_count <= SCENERY_MAX_VERTICES_X:
                        obj.select = True
                else:
                    if self.props.export_mesh_type == "collision" or vertex_count < GENERAL_MAX_VERTICES_X or obj == self.objects_to_export[-1]:
                        obj.select = True
                
            # Transform for General mesh & Ground
            if self.props.export_mesh_type == "general" or self.props.export_mesh_type == "scenery":
                bpy.ops.transform.mirror(
                    constraint_axis=(False, False, True),
                    constraint_orientation='GLOBAL',
                    proportional='DISABLED'
                )
                bpy.ops.transform.rotate(
                    axis = (90, 0 , 0),
                    constraint_axis=(True, False, False),
                    constraint_orientation='GLOBAL',
                    proportional='DISABLED'
                )
            
            
            filename = eval("self.props.export_basename_" + self.props.export_mesh_type)
            ExportVertexColors = True
            
            # collision mesh
            if self.props.export_mesh_type == "collision":
                ExportVertexColors = False
            
                
            if self.files_exported > 0:
                filename += str(self.files_exported + 1)
            
            filename += ".x"

            filePath = os.path.join(bpy.path.abspath(self.props.export_path), filename)
            
            try:
                bpy.ops.export_scene.x(
                    filepath = filePath,
                    SelectedOnly = True,
                    CoordinateSystem = 'LEFT_HANDED',
                    UpAxis = 'Y',
                    ExportMeshes = True,
                    ExportNormals = True,
                    FlipNormals = False,
                    ExportUVCoordinates = True,
                    ExportMaterials = True,
                    ExportActiveImageMaterials = False,
                    ExportVertexColors = ExportVertexColors,
                    ExportSkinWeights = False,
                    ApplyModifiers = False,
                    ExportArmatureBones = False,
                    ExportRestBone = False,
                    ExportAnimation = False,
                    IncludeFrameRate = False,
                    ExportActionsAsSets = False,
                    AttachToFirstArmature = False,
                    Verbose = False

                )
            except:
                print("Error during exporting to X")
                self.report({'ERROR'}, "Error when saving DirectX file, check you have the DirectX addon enabled and your output path is correct!")
                return False
            
            self.files_exported += 1

            for obj in context.selected_objects:
                self.objects_to_export.remove(obj)
            
            if self.objects_to_export:
                exportChunks()
                
        if self.props.apply_transformations:
            bpy.ops.object.transform_apply(location = True, scale = True, rotation = True)

        view3d = getView3D()
        view3d.pivot_point='BOUNDING_BOX_CENTER'


        exportChunks()

        bpy.ops.object.rotation_clear()
        bpy.ops.object.scale_clear()

        print( "\n==========================")
        print("COMPLETE - files exported: " + str(self.files_exported))
        print( "==========================")
        # self.report({'INFO'}, "Files Exported: " + str(self.files_exported))

        # bpy.ops.object.select_all(action="DESELECT")

        return {'FINISHED'}


class Split(bpy.types.Operator):
    
    bl_idname = "object.split_for_rbr"
    bl_label = "Split"
    bl_description = "Split selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):

        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "No object selected!")
            return {'CANCELLED'}
        
        # only 1 selected object allowed
        if len(context.selected_objects) > 1:
            self.report({'ERROR'}, "Select single object")
            return {'CANCELLED'}
        
        # no modifiers allowed
        if len(context.selected_objects[0].modifiers) > 0:
            self.report({'ERROR'}, "Apply modifiers first")
            return {'CANCELLED'}
    
        props = context.scene.export_for_rbr_props
        
        def cut_object( obj ):
            #Gets the bounds
            bounds = [b[:] for b in obj.bound_box]
            #0 is the min
            min_bounds = Vector( bounds[0] )
            
            #6 is opposite corner to 0
            max_bounds = Vector( bounds[6] )
            delta_bounds = max_bounds - min_bounds
            
            #Get the axis which corresponds to the largest area
            axis = max_axis( delta_bounds )

            #The center is the limit    
            limit = min_bounds[axis] + 0.5 * delta_bounds[axis]

            #Set the object active
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.context.scene.objects.active = obj
            #Set selection mode
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")
            
            
            #Select the wanted vertices
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
            for v in obj.data.vertices:
                v.select = v.co[axis] < limit
            
            #Extend to linked parts (so wont cut the faces or edges)    
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_linked()
            
            #Get the selected vertex count
            obj.update_from_editmode()
            selected_verts_count = len([v for v in obj.data.vertices if v.select])
            
            # needs_after_cleanup = False 
            
            if selected_verts_count == len(obj.data.vertices):
            
                print("Skipping select linked as whole mesh is linked ...")
                bpy.ops.mesh.select_all(action = 'DESELECT')
                bpy.ops.object.mode_set(mode = 'OBJECT')
                
                for v in obj.data.vertices:
                    v.select = v.co[axis] < limit
                        
                bpy.ops.object.mode_set(mode="EDIT")
                
                # needs_after_cleanup = True 
            
            obj.update_from_editmode()
            selected_verts_count = len([v for v in obj.data.vertices if v.select])
            selected_faces_count = len([f for f in obj.data.polygons if f.select])
            
            print( "\nSplitting Along Axis: " + str( axis ) )
            print( "Verts to separate: " + str( selected_verts_count ) + "/" + str( len( obj.data.vertices ) ) )
            print( "Polygons to separate:" + str(selected_faces_count))

            #Check that will separate something
            result = True
            
            if selected_faces_count > 0 and len(obj.data.polygons) > 1:
                print("\nSEPARATING " + str(selected_verts_count) + " vertices...")
                # bpy.ops.mesh.select_mode(type="FACE")
                bpy.ops.mesh.separate(type='SELECTED') 
                
            else:
                result = False
            
            bpy.ops.mesh.select_all(action = 'SELECT')                
            
            # print("\nCLEANING...")

            # bpy.ops.mesh.reveal()

            # if props.remove_doubles:
            #     bpy.ops.mesh.remove_doubles(threshold = props.remove_doubles_threshold, use_unselected = True)
            
            # if props.delete_loose:
            #     bpy.ops.mesh.delete_loose()

            bpy.ops.mesh.select_all(action = 'DESELECT')
            
            bpy.ops.object.mode_set(mode="OBJECT")

            return result
            
         # Get the axis corresponding to the largest dimension
        def max_axis( vector ):
            axis = 0
            result = vector.x
            if result < vector.y:
                axis = 1
                result = vector.y
            #Remove the 3 following line if the cut along z does not work
            if result < vector.z:
                axis = 2
                result = vector.z
            return axis
            
        # Return true if one of bounds dimension is longer than max_length
        def is_too_long ( obj ):
            
            bounds = [b[:] for b in obj.bound_box]
            min_bounds = Vector( bounds[0] )
            max_bounds = Vector( bounds[6] )
            delta_bounds = max_bounds - min_bounds
            
            # longest = delta_bounds.x
            
            # if delta_bounds.y > delta_bounds.x:
                # longest = delta_bounds.y
            # elif delta_bounds.z > delta_bounds.x:
                # longest = delta_bounds.z
                
            # scenery
            
            if props.export_mesh_type == "scenery":
                return False
            
            if props.export_mesh_type == "general":
                max_length = GENERAL_MAX_LENGTH
            
            if props.export_mesh_type == "collision":
                return False
            
            if delta_bounds.x > max_length or delta_bounds.y > max_length or delta_bounds.z > max_length:
                return True
        
        def is_too_dense ( obj ):
        
            
            if props.export_mesh_type == "scenery":
                max_vertices = SCENERY_MAX_VERTICES
            
            if props.export_mesh_type == "general":
                max_vertices = GENERAL_MAX_VERTICES
                
            if props.export_mesh_type == "collision":
                return False
            
            if len(obj.data.vertices) >=  max_vertices:
                return True
            
            return False
            
        
        start_time = time.time()
        
        
        #Preparing & cleaning meshes
        print( "\nCLEANUP")
        print( "=====================\n")

        selected_objs = bpy.context.selected_objects
        for obj in selected_objs:

            bpy.context.scene.objects.active = obj

            if props.apply_transformations:
                bpy.ops.object.transform_apply(location = True, scale = True, rotation = True)
            
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action = 'SELECT')

            if props.remove_doubles:
                bpy.ops.mesh.remove_doubles(threshold = props.remove_doubles_threshold, use_unselected = True)
            
            if props.delete_loose:
                bpy.ops.mesh.delete_loose()
                    
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")
            
            obj.update_from_editmode()
        
            if props.separate_by_material:
                print("\nSeparating by material ...")
                bpy.ops.mesh.separate(type='MATERIAL')
        
        print("Done.")
        
        print( "\nSPLITTING")
        print( "=====================")
        iteration = 0
        chunks_to_process = 0
        found = True
        
        while found:
            
            found = False
            chunks_to_process = 0

            #Get all objects that have more than the wanted vertex amount
            for obj in [x for x in bpy.context.selected_objects if is_too_dense(x) or is_too_long(x)]:
                chunks_to_process += 1
                if cut_object( obj ):
                    found = True
            iteration += 1            
            print( "Iteration: " + str( iteration ) + "   Objects: " + str( len( bpy.context.selected_objects ) ) )

        print( "\n==========================")
        print("SPLITTING FINISHED in: " + str( time.time() - start_time ) )
        print("\nImperfect chunks: " + str(chunks_to_process))

        print( "==========================\n")
        
        return {'FINISHED'}
        
class ExportForRBR_Panel(bpy.types.Panel):

    bl_idname = "panel.export_for_rbr"
    bl_label = "Export for RBR"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        return bpy.context.selected_objects and type(context.active_object.data) == bpy.types.Mesh

    def draw(self, context):
        layout =  self.layout
        
        # if context.scene.export_for_rbr_props.export_mesh_type == "general":
            # layout.label("Splitting Options:", icon="MOD_DECIM")
            
            # box = layout.box()
            # row = box.row(align=True)
            
            # row.prop(context.scene.export_for_rbr_props, "max_vertices", text="Vertex Count")
            # row.prop(context.scene.export_for_rbr_props, "max_length", text="Length")

            # layout.row().separator()

        layout.label("Cleanup Options:", icon="SCRIPT")

        box = layout.box()
        
        #row = box.row()
        #row.prop(context.scene.export_for_rbr_props, "apply_transformations", text="Apply Transformation")

        #row = box.row()
        #row.prop(context.scene.export_for_rbr_props, "separate_by_material", text="Separate by Material")

        #row = box.row()
        #row.prop(context.scene.export_for_rbr_props, "delete_loose", text="Delete Loose")
        
        row = box.row()
        row.prop(context.scene.export_for_rbr_props, "remove_doubles", text="Remove Doubles")
        
        if context.scene.export_for_rbr_props.remove_doubles:
            row.prop(context.scene.export_for_rbr_props, "remove_doubles_threshold", text="Distance", slider=True)
        

        layout.row().separator()
        
        
        layout.label("Export Options:", icon="EXPORT")

        box = layout.box()
        row = box.row()
        row.prop(context.scene.export_for_rbr_props, "export_mesh_type", text="Mesh Type")


        # if context.scene.export_for_rbr_props.export_mesh_type == "general":
            # row = box.row()
            # row.label("Vertex Count per File:")
            # row.prop(context.scene.export_for_rbr_props, "max_vertices_x", text="")
        
        row = box.row()
        if context.scene.export_for_rbr_props.export_mesh_type == "general":
            row.prop(context.scene.export_for_rbr_props, "export_basename_general", text="File Name")
        
        if context.scene.export_for_rbr_props.export_mesh_type == "collision":
            row.prop(context.scene.export_for_rbr_props, "export_basename_collision", text="File Name")
            
        if context.scene.export_for_rbr_props.export_mesh_type == "scenery":
            row.prop(context.scene.export_for_rbr_props, "export_basename_scenery", text="File Name")

        row = box.row()
        row.prop(context.scene.export_for_rbr_props, "export_path", text="Output Folder")
        

        layout.row().separator()
        

        row = layout.row()
        row.scale_y = 2.0

        if context.scene.export_for_rbr_props.export_mesh_type == "collision":
            row.operator("object.export_x_rbr", icon="EXPORT")
            #row = layout.row(align=True)
            #row.operator("object.split_for_rbr", icon="MOD_DECIM")
        
        else:
            row.operator("object.split_export_rbr", icon="AUTO")
            


class ExportForRBR_Properties(PropertyGroup):


    remove_doubles = BoolProperty(
        default=True,
        description="This will double all the removes"
    )
    remove_doubles_threshold = FloatProperty(
        min=0.0001,
        max=1,
        default=0.05,
        unit='LENGTH',
        description="Vertices within the distance will be merged"
    )
    delete_loose = BoolProperty(
        default=True,
        description="This will enable or disable the checkbox"
    )
    apply_transformations = BoolProperty(
        default=True,
        description="Applies position, rotation and scale (makes no sense to disable it as it will cause wrong transformation in RBR editor... but whatever!"
    )
    max_vertices = IntProperty(
        min=0,
        default=25000,
        description="Maximum vertices per chunk - RBR editor can only import files with meshes consisting of < 30 000 vertices"
    )
    max_length = FloatProperty(
        min=0,
        default=200,
        unit='LENGTH',
        description="Meshes will be splitted if they are longer than the given distance (usually 200-500m is fine for RBR).\n(Too long meshes won't display in game)"
    )
    separate_by_material = BoolProperty(
        default=True,
        description="Splits the selected meshes by material - no reason to uncheck it as RBR can work only with 1 material per object"
    )
    max_vertices_x = IntProperty(
        min=0,
        default=400000,
        description="Maximum vertices per one DirectX file (to keep the filesize below the limit for imported .x into RBR editor)"
    )
    export_mesh_type = EnumProperty(
        items = (('general','General & Ground Mesh','', "EDITMODE_HLT", 0),('collision','Collision Mesh','', "WIRE", 1),('scenery','Scenery','', "WORLD_DATA", 2)),
        name="RBR Mesh Type",
        description = "Type of the exported mesh - general & ground mesh will be rotated & mirrored, so it imports correctly into RBR editor\n"
    )
    export_path = StringProperty(
        name="",
        description="Target folder for exported DirectX files",
        default="//",
        maxlen=2048,
        subtype='DIR_PATH'
    )
    export_basename_general = StringProperty(
        name="",
        default = "mesh",
        description="File name for exported DirectX files",
        maxlen=1024
    )
    export_basename_collision = StringProperty(
        name="",
        default = "collision",
        description="File name for exported DirectX files",
        maxlen=1024
    )
    export_basename_scenery = StringProperty(
        name="",
        default = "scenery",
        description="File name for exported DirectX files",
        maxlen=1024
    )
    
# def getDefaultExportBaseName():
    # try:
        # export_basename = bpy.path.display_name_from_filepath(bpy.data.filepath)
    # except:
        # export_basename == ""
        
    # if export_basename == "":
        # export_basename = "export"
    
    # return export_basename

#@persistent
#def on_scene_update(scene):
#   if scene.export_for_rbr_props.export_basename == "":
#        scene.export_for_rbr_props.export_basename = getDefaultExportBaseName()
    

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.export_for_rbr_props = PointerProperty(type=ExportForRBR_Properties)
    #bpy.app.handlers.scene_update_pre.append(on_scene_update)


def unregister():
    #bpy.app.handlers.scene_update_pre.remove(on_scene_update)
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.export_for_rbr_props

if __name__ == "__main__":
    register()