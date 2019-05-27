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
    stride = 1
    if(type == SourceType.float4x4):
        stride = 16
    accessor.set('count', str(int(count/stride)))
    accessor.set('stride', str(stride))
    
    param = ET.SubElement(accessor, 'param')
    param.set('name', dataName)
    param.set('type', type.name)

def matrixToStrList(mat, transpose):
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
        matText = matrixToStrList(cb.matrix_basis.copy(), True)
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
        
    matText = matrixToStrList(obj.matrix_world.copy(), True)
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
    matText = matrixToStrList(obj.matrix_world.copy(), True)
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
        bsmat.text = matrixToStrList(obj.matrix_world.copy(), True)
        joints = ET.SubElement(skin, 'joints')
        
        bones = obj.pose.bones
        bonesNameList = ' '.join( b.name for b in bones )
        sourceName_0 = c + '.joints'
        buildSource(skin, bonesNameList, len(bones), sourceName_0, 'JOINT', SourceType.string)
        inputNameList = ET.SubElement(joints, 'input')
        inputNameList.set('source', '#' + sourceName_0)
        inputNameList.set('semantic', 'JOINT')
        
        boneMats = []
        for b in bones:
            boneMatrix = b.matrix.copy()
            boneMatrix.inverted()
            boneMats.append(matrixToStrList(boneMatrix, True))
        boneMatrixList = ' '.join( str for str in boneMats )
        sourceName_1 = c + '.inverse.bind.matrix'
        buildSource(skin, boneMatrixList, len(bones) * 16, sourceName_1, 'TRANSFORM', SourceType.float4x4)
        inputIBMList = ET.SubElement(joints, 'input')
        inputIBMList.set('source', '#' + sourceName_1)
        inputIBMList.set('semantic', 'INV_BIND_MATRIX')

        weightDictionary = {}
        weights = []
        vcount = []
        v = []
        vertices = mesh.vertices
        for vert in vertices:
            vcount.append(len(vert.groups))
            for g in vert.groups:
                if( g.weight not in weightDictionary ):
                    weightDictionary[g.weight] = len(weights)
                    weights.append(g.weight)
                weightIndex = weightDictionary[g.weight]
                v.append(g.group)
                v.append(weightIndex)
                
        sourceName_2 = c + '.skin.weights'
        weightsStr = ' '.join( str(w) for w in weights)
        buildSource(skin, weightsStr, len(weights), sourceName_2, 'WEIGHT', SourceType.float)
        
        vertexWeightDom = ET.SubElement(skin, 'vertex_weights')
        vertexWeightDom.set('count', str(len(vcount)))
        inputJoints = ET.SubElement(vertexWeightDom, 'input')
        inputJoints.set('source', '#' + sourceName_0)
        inputJoints.set('semantic', 'JOINT')
        inputJoints.set('offset', '0')
        
        inputWeight = ET.SubElement(vertexWeightDom, 'input')
        inputWeight.set('source', '#' + sourceName_2)
        inputWeight.set('semantic', 'WEIGHT')
        inputWeight.set('offset', '1')
        
        vcountDom = ET.SubElement(vertexWeightDom, 'vcount')
        vcountDom.text = ' '.join(str(val) for val in vcount )
        vDom = ET.SubElement(vertexWeightDom, 'v')
        vDom.text = ' '.join(str(val) for val in v )
        
        print(weights)
        print(vcount)
        print(v)

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
    
#### comment this test output part when deploying. ####
#export(bpy.context, r'D://projects//dae_library//assets//dev.dae')