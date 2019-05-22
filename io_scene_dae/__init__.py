bl_info = {
    'name': 'Collada Exporter',
    'location': "File > Import-Export",
    'author': 'Jinger Li',
    'category': 'Import-Export',
}

import bpy
#import imp
#if( "collada_exporter" in locals()):
#    imp.reload(collada_exporter)
#else:
#    imp.load

class DAEExporter(bpy.types.Operator):
    """My Object Moving Script"""      # blender will use this as a tooltip for menu items and buttons.
    bl_idname = 'dae.exporter'        # unique identifier for buttons and menu items to reference.
    bl_label = 'Collada Exporte'    # display name in the interface.
    bl_options = {'PRESET'}  # enable undo for the operator.

    def execute(self, context):        # execute() is called by blender when running the operator.
        print('Hello World.')
        return {'FINISHED'}            # this lets blender know the operator finished successfully.

def menu_func(self, context):
    self.layout.operator(DAEExporter.bl_idname, text="Collada (.dae)")
     
def register():
    #bpy.utils.register_module(__name__)
    bpy.utils.register_class(DAEExporter)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    #bpy.utils.register_module(__name__)
    bpy.utils.unregister_class(DAEExporter)
    bpy.types.INFO_MT_file_export.remove(menu_func)

# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    register()