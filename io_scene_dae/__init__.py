bl_info = {
    'name': 'Collada Exporter',
    'location': "File > Import-Export",
    'author': 'Jinger Li',
    'category': 'Import-Export',
}

import bpy
import imp
if( "collada_exporter" in locals()):
    imp.reload(collada_exporter)

from . import collada_exporter

class DAEExporter(bpy.types.Operator):
    """My Object Moving Script"""      # blender will use this as a tooltip for menu items and buttons.
    bl_idname = 'dae.exporter'        # unique identifier for buttons and menu items to reference.
    bl_label = 'Collada Exporte'    # display name in the interface.
    bl_options = {'PRESET'}  # enable undo for the operator.
    
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):        # execute() is called by blender when running the operator.
        collada_exporter.export(context, self.filepath)
        return {'FINISHED'}            # this lets blender know the operator finished successfully.

def menu_func(self, context):
    self.layout.operator(DAEExporter.bl_idname, text="Collada (.dae)")
     
def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    register()