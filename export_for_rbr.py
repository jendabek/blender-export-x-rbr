#TODO select chunks after export
#TODO weird scene on_update errors when disabling addon?
#TODO display status messages in the panel
#TODO labels, texts etc.
#TODO overall refactoring

bl_info = {
    "name": "Simtraxx - Export for RBR",
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

class SplitAndExport(bpy.types.Operator):

    bl_idname = "object.split_export_rbr"
    bl_label = "Split & Export X"
    bl_options = {'REGISTER', 'UNDO'}

    
    def execute(self, context):
        Split.execute(self, context)
        ExportX.execute(self, context)
        return {"FINISHED"}


class ExportX(bpy.types.Operator):

    bl_idname = "object.export_x_rbr"
    bl_label = "Export X"
    bl_options = {'REGISTER', 'UNDO'}

    files_exported = 0
    objects_to_export = None
    props = None
    
    def execute(self, context):

        self.props = context.scene.export_for_rbr_properties
        self.objects_to_export = context.selected_objects
        self.files_exported = 0

        
        print( "\nEXPORTING TO X")
        print( "=====================\n")

        if len(self.objects_to_export) == 0:
            return {"FINISHED"}

        
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
                if self.props.max_vertices_x == 0 or vertex_count < self.props.max_vertices_x or obj == self.objects_to_export[-1]:
                    obj.select = True
                
            # Transform for General mesh & Ground
            if self.props.export_mesh_type == "0":
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
            

            self.props.export_basename.strip()
            if self.props.export_basename == "":
                self.props.export_basename = getDefaultExportBaseName()

            filePath = os.path.join(bpy.path.abspath(self.props.export_path), self.props.export_basename + "-" + str(self.files_exported + 1) + ".x")
            
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
                    ExportVertexColors = True,
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
                self.report({'ERROR'}, "Error when saving DirectX file")
                return False
            
            # files_exported = files_exported + 1
            
            
            self.files_exported += 1

            for obj in context.selected_objects:
                self.objects_to_export.remove(obj)
            
            if self.objects_to_export:
                exportChunks()
                

        
        bpy.ops.object.transform_apply(location = True, scale = True, rotation = True)

        view3d = getView3D()
        view3d.pivot_point='BOUNDING_BOX_CENTER'


        exportChunks()

        print( "\n==========================")
        print("COMPLETE - files exported: " + str(self.files_exported))
        print( "==========================")
        # self.report({'INFO'}, "Files Exported: " + str(self.files_exported))

        bpy.ops.object.select_all(action="DESELECT")

        return {'FINISHED'}


class Split(bpy.types.Operator):
    
    bl_idname = "object.split_for_rbr"
    bl_label = "Split"
    bl_options = {'REGISTER', 'UNDO'}
    

    def execute(self, context):
    
        properties = context.scene.export_for_rbr_properties
        
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
                bpy.ops.mesh.separate(type='SELECTED') 
                
            else:
                result = False
            
            
            bpy.ops.mesh.select_all(action = 'SELECT')                
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.delete_loose()
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
            
        # Return true if one of bounds dimension is longer than max_dimension
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
                
            # return longest
            if properties.max_dimension == 0:
                return False
            if delta_bounds.x > properties.max_dimension or delta_bounds.y > properties.max_dimension or delta_bounds.z > properties.max_dimension:
                return True
        
        def is_too_dense ( obj ):
            if  properties.max_vertices == 0:
                return False
            
            if len(obj.data.vertices) >=  properties.max_vertices:
                return True
            
            return False
            
        
        start_time = time.time()
        
        obj =  bpy.context.scene.objects.active
        
        if obj == None:
            print ("No object selected!")
            return {'FINISHED'}
        
        #Preparing & cleaning mesh
        
        print( "\nCLEANUP")
        print( "=====================\n")
        bpy.ops.object.transform_apply(location = True, scale = True, rotation = True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.select_all(action = 'DESELECT')        
        bpy.ops.object.mode_set(mode="OBJECT")
        
        obj.update_from_editmode()
        
        if  properties.separate_by_material:
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
                chunks_to_process = chunks_to_process + 1
                if cut_object( obj ):
                    found = True
            iteration += 1            
            print( "Iteration: " + str( iteration ) + "   Objects: " + str( len( bpy.context.selected_objects ) ) )

        print("\nFailed chunks: " + str(chunks_to_process))
        print( "\n==========================")
        print("SPLITTING FINISHED in: " + str( time.time() - start_time ) )
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
        return context.active_object is not None

    def draw(self, context):
        layout =  self.layout
        
        box = layout.box()

        row = box.row()
        row.label("Splitting Limits:")

        row = box.row(align=True)
        row.prop(context.scene.export_for_rbr_properties, "max_vertices", text="Vertices")
        row.prop(context.scene.export_for_rbr_properties, "max_dimension", text="Length")
        
        row = box.row()
        
        box = layout.box()
        
        row = box.row()
        row.label("Export Options:")

        row = box.row()
        row.prop(context.scene.export_for_rbr_properties, "export_mesh_type", text="Mesh Type", expand=True)

        row = box.row()
        row.prop(context.scene.export_for_rbr_properties, "max_vertices_x", text="Vertices per X")

        row = box.row()
        row.prop(context.scene.export_for_rbr_properties, "export_basename", text="File Name")

        row = box.row()
        row.prop(context.scene.export_for_rbr_properties, "export_path", text="Output Folder")
        
        row = layout.row()
        row.scale_y = 2.0
        row.operator("object.split_export_rbr", icon="EXPORT")
        
        row = layout.row(align=True)
        # split = row.split(percentage=0.7, align=True)
        row.operator("object.split_for_rbr", icon="UV_ISLANDSEL")
        row.operator("object.export_x_rbr",icon="EXPORT")
        

class ExportForRBR_Properties(PropertyGroup):

    max_vertices = IntProperty(
        min=0,
        default=25000
    )
    max_dimension = IntProperty(
        min=0,
        default=200
    )
    separate_by_material = BoolProperty(
        default=True
    )

    max_vertices_x = IntProperty(
        min=0,
        default=800000
    )

    export_mesh_type = EnumProperty(
        items = (('0','General & Ground Mesh','', "WORLD_DATA", 0),('1','Collision Mesh','', "GRID", 1))
    )
    export_path = StringProperty(
        name="",
        description="Path to Directory",
        default="//",
        maxlen=2048,
        subtype='DIR_PATH')
    
    export_basename = StringProperty(
        name="",
        description="Name of the file",
        maxlen=1024)
    
def getDefaultExportBaseName():
    try:
        export_basename = bpy.path.display_name_from_filepath(bpy.data.filepath)
    except:
        export_basename == ""
        
    if export_basename == "":
        export_basename = "export"
    
    return export_basename

@persistent
def on_scene_update(scene):
    if scene.export_for_rbr_properties.export_basename == "":
        scene.export_for_rbr_properties.export_basename = getDefaultExportBaseName()
    

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.export_for_rbr_properties = PointerProperty(type=ExportForRBR_Properties)
    bpy.app.handlers.scene_update_pre.append(on_scene_update)


def unregister():
    bpy.app.handlers.scene_update_pre.remove(on_scene_update)
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.export_for_rbr_properties

if __name__ == "__main__":
    register()