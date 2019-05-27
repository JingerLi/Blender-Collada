import bpy
import numpy
from enum import Enum
import xml.etree.ElementTree as ET

mesh_targets = {}
controller_targets = {}

class SourceType(Enum):
    string = 0
    float = 1
    float4x4 = 2

def buildSource(domNode, strdata, count, id, dataName, type=SourceType.float):
    sourceNode = ET.SubElement(domNode, 'source')
    sourceNode.set('id', id)
    data = None
    if(type == SourceType.string):
        data = ET.SubElement(sourceNode, 'Name_array')
    else:
        data = ET.SubElement(sourceNode, 'float_array')
    data.set('id', id + '.data')
    data.set('count', str(count))
    data.text = strdata
    
    techcom = ET.SubElement(sourceNode, 'technique_common')
    accessor = ET.SubElement(techcom, 'accessor')
    accessor.set('source', '#' + id + '.data')
    accessor.set('count', str(count))
    stride = '1'
    if(type == SourceType.float4x4):
        stride = '16'
    accessor.set('stride', stride)
    
    param = ET.SubElement(accessor, 'param')
    param.set('name', dataName)
    param.set('type', type.name)

def matrixToStrList(matrix, transpose):
    mat = matrix.copy()
    if(transpose):
        mat.transpose()
    vals = numpy.asarray(mat).ravel()
    matText = ' '.join(str(x) for x in vals )
    return matText

def loadBonesTree( root, domNode, namebase ):
    boneStack = []
    domStack = []
    boneStack.append(root)
    domStack.append(domNode)
    while len(boneStack) != 0:
        cb = boneStack.pop()
        dom = domStack.pop()
        name = cb.name
        dom.set('id', namebase + '.' + name)
        dom.set('sid', name)
        dom.set('type', 'JOINT')
        
        matrix = ET.SubElement(dom, 'matrix')
        matText = matrixToStrList(cb.matrix, True)
        matrix.text = matText
        for c in cb.children:
            dc = ET.SubElement(dom, 'node')
            boneStack.append(c)
            domStack.append(dc)
    
def loadNodeArmature(obj, domNode):
    print('type: ' + obj.name)
    armature = obj.data
    posePosition = armature.pose_position
    armature.pose_position = 'REST'
        
    matText = matrixToStrList(obj.matrix_world, True)
    matNode = ET.SubElement(domNode, 'matrix')
    matNode.text = matText
    
    roots = []
    pose = obj.pose
    for b in pose.bones:
        if(b.parent == None):
            roots.append(b)
    for r in roots:
        boneRoot = ET.SubElement(domNode, 'node')
        loadBonesTree(r, boneRoot, obj.name)
    armature.pose_position = posePosition
    
def loadNodeMesh(obj, domNode ):
    matText = matrixToStrList(obj.matrix_world, True)
    matNode = ET.SubElement(domNode, 'matrix')
    matNode.text = matText
    
    mesh = obj.data
    mesh_targets[mesh.name] = mesh
    instGeo = ET.SubElement(domNode, 'instance_geometry')
    instGeo.set('url', '#' + mesh.name)
    
    for m in obj.modifiers:
        id = m.name + '.' + obj.name + '.skin'
        instCtrl = ET.SubElement(domNode, 'instance_controller')
        instCtrl.set('url',  '#' + id)
        ctrlMeta = { 'mesh': mesh,  'modifier': m}
        controller_targets[id] = ctrlMeta

def loadLibControllers( lib_controllers ):
    for c in controller_targets:
        meta = controller_targets[c]
        mesh = meta['mesh']
        obj = meta['modifier'].object
        armature = obj.data
         
        ctrl = ET.SubElement(lib_controllers, 'controller')
        ctrl.set('id', c)
        ctrl.set('name', obj.name)
        
        skin = ET.SubElement(ctrl, 'skin')
        skin.set('source', '#' + mesh.name)
        
        bsmat = ET.SubElement(skin, 'bind_shape_matrix')
        bsmat.text = matrixToStrList(obj.matrix_world, True)
        
        bones = obj.data.bones
        bonesNameList = ' '.join( b.name for b in bones )
        buildSource(skin, bonesNameList, len(bones), c + '.joints', 'JOINT', SourceType.string)

def loadLibGeometries( lib_geometries ):
    ET.SubElement(lib_geometries, 'mesh')
    print("TODO load geometries.")

def loadLibVisualScene( lib_visual_scene ):
    objscene = bpy.data.scenes[0]
    domScene = ET.SubElement(lib_visual_scene, 'visual_scene')
    objs = objscene.objects
    for obj in objs:
        objName = obj.name
        objType = obj.type
        domNode = ET.SubElement(domScene, 'node')
        domNode.set('id', objName)
        domNode.set('obj_type', objType)
        domNode.set('type', 'NODE')   
        if(obj.type == 'MESH'):
            loadNodeMesh(obj, domNode)
        elif(obj.type == 'ARMATURE'):
            loadNodeArmature(obj, domNode)

def prettify( root ):
    lvstack = []
    elmstack = []
    lvstack.append(0)
    elmstack.append(root)
    while len(elmstack) != 0:
        lv = lvstack.pop()
        p = elmstack.pop()
        if(len(p) != 0 ):
            p.text = '\n' + (lv + 1) * '\t'
            for c in reversed(p):
                c.tail = '\n' + (lv + 1) * '\t'
                elmstack.append(c)
                lvstack.append(lv + 1)
            p[-1].tail = '\n' + lv * '\t'

def export( context, filepath ):
    collada = ET.Element('COLLADA')
    collada.set('xmlns', 'http://www.collada.org/2005/11/COLLADASchema')
    collada.set('version', '1.5.0')
    collada.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    
    lib_geometries = ET.SubElement(collada, 'library_geometries')    
    lib_animations = ET.SubElement(collada, 'library_animations')
    lib_controllers = ET.SubElement(collada, 'library_controllers')
    lib_visual_sence = ET.SubElement(collada, 'library_visual_scenes')
    
    loadLibGeometries(lib_geometries)
    loadLibVisualScene(lib_visual_sence)
    loadLibControllers(lib_controllers)
    
    prettify(collada)
    tree = ET.ElementTree(collada)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)