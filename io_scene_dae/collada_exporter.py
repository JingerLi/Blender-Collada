import bpy
import numpy
import mathutils
from enum import Enum
from mathutils import Matrix, Quaternion, Vector
import xml.etree.ElementTree as ET

import os
os.system('cls')

mesh_targets = {}
controller_targets = {}
images = {}

class SourceType(Enum):
    Name_array = 0
    float_array = 1

class DataType(Enum):
    string = 0
    float = 1
    float4x4 = 2

class Param:
    name = ''
    type = DataType.string
    def __init__(self, n, t):
        self.name = n
        self.type = t

def addInputBlock(domNode, semantic, source, offset=None):
    input = ET.SubElement(domNode, 'input')
    input.set('semantic', semantic)
    input.set('source', source)
    if(offset != None):
        input.set('offset', str(offset))
        
def buildSource(domNode, strdata, count, id, params, sourceType=SourceType.float_array):
    sourceNode = ET.SubElement(domNode, 'source')
    sourceNode.set('id', id)
    data = ET.SubElement(sourceNode, sourceType.name)

    data.set('id', id + '.data')
    data.set('count', str(count))
    data.text = strdata
    
    techcom = ET.SubElement(sourceNode, 'technique_common')
    accessor = ET.SubElement(techcom, 'accessor')
    accessor.set('source', '#' + id + '.data')
    stride = 0
    for p in params:
        t = p.type
        param = ET.SubElement(accessor, 'param')
        param.set('name', p.name)
        param.set('type', t.name)
        if( t == DataType.string or t == DataType.float):
            stride += 1
        elif ( t == DataType.float4x4 ):
            stride += 16
    if(stride != 0):
        accessor.set('count', str(int(count/stride)))
        accessor.set('stride', str(stride))

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
        matrix.set('sid', 'LOCALBINDING')
        matrixInv = ET.SubElement(dom, 'matrix')
        matrixInv.set('sid', 'INVBINDING')
        matText = ''
        matInvText = ''
        if(cb.parent == None):
            matText = matrixToStrList(cb.matrix_local.copy(), True)
            matInvText = matrixToStrList(Matrix.Identity(4), True)
        else:
            parentLocalMat = cb.parent.matrix_local.copy()
            parentLocalMat.invert()
            localMat= cb.matrix_local * parentLocalMat
            matText = matrixToStrList(localMat, True)
            invBindMat = cb.matrix_local.copy()
            invBindMat.invert()
            matInvText = matrixToStrList(invBindMat, True)
            
        matrix.text = matText
        matrixInv.text = matInvText
        for c in cb.children:
            dc = ET.SubElement(dom, 'node')
            boneStack.append(c)
            domStack.append(dc)
    
def loadNodeArmature(obj, domNode):
    armature = obj.data   
    matText = matrixToStrList(obj.matrix_world.copy(), True)
    matNode = ET.SubElement(domNode, 'matrix')
    matNode.text = matText
    
    roots = []
    bones = armature.bones;
    for b in bones:
        if(b.parent == None):
            roots.append(b)
    for r in roots:
        boneRoot = ET.SubElement(domNode, 'node')
        loadBonesTree(r, boneRoot, obj.name)
    
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
        ctrlMeta = { 'object': obj, 'mesh': mesh,  'modifier': m}
        controller_targets[id] = ctrlMeta

def loadLibControllers( lib_controllers ):
    for c in controller_targets:
        meta = controller_targets[c]
        obj = meta['object']
        mesh = meta['mesh']
        modifier = meta['modifier'].object
        
        vGroups = obj.vertex_groups
        sourceName_0 = c + '.groups'
        vertGroups = []
        for vg in vGroups:
             vertGroups.append(vg.name)
        bonesNameList = ' '.join( n for n in vertGroups)
 
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
        print(len(weights))
        sourceName_2 = c + '.skin.weights'
        weightsStr = ' '.join( str(w) for w in weights)    
            
        ctrl = ET.SubElement(lib_controllers, 'controller')
        ctrl.set('id', c)
        ctrl.set('name', modifier.name)
        
        skin = ET.SubElement(ctrl, 'skin')
        skin.set('source', '#' + mesh.name)
        
        bsmat = ET.SubElement(skin, 'bind_shape_matrix')
        object = meta['object'];
        bsmat.text = matrixToStrList(object.matrix_local.copy(), True)
        
        buildSource(skin, bonesNameList, len(vGroups), sourceName_0, [ Param('GROUPS',DataType.string) ], SourceType.Name_array)
        buildSource(skin, weightsStr, len(weights), sourceName_2, [Param('WEIGHT',DataType.float)], SourceType.float_array)
                 
        vertexWeightDom = ET.SubElement(skin, 'vertex_weights')
        vertexWeightDom.set('count', str(len(vcount)))
        addInputBlock(vertexWeightDom, 'GROUPS', '#' + sourceName_0, 0)
        addInputBlock(vertexWeightDom, 'WEIGHT', '#' + sourceName_2, 1)
        
        vcountDom = ET.SubElement(vertexWeightDom, 'vcount')
        vcountDom.text = ' '.join(str(val) for val in vcount )
        vDom = ET.SubElement(vertexWeightDom, 'v')
        vDom.text = ' '.join(str(val) for val in v )

def loadLibGeometries( lib_geometries ):
    for g in mesh_targets:  
        mesh = mesh_targets[g]
        vertices = mesh.vertices
        vertPosStrs = []
        for v in vertices:
            vertPosStrs.append(' '.join( str(val) for val in v.co ))
        sourceNamePos = g + '.vertex.position'
        vertStrData = ' '.join( str for str in vertPosStrs)
        
        loops = mesh.loops
    
        uvSet = 0
        allUVCoordsName = []
        allUVCoords = []
        uvLayers = mesh.uv_layers
        for uvLayer in uvLayers:
            uvData = uvLayer.data
            uvCoords = ['0.0 0.0'] * len(vertices)
            for li in range(len(loops)):
                vi = loops[li].vertex_index
                uvCoords[vi] = ' '.join( str(val) for val in uvData[li].uv )
            allUVCoordsName.append( g + '.uvlayer' + str(uvSet))
            allUVCoords.append(uvCoords)
            uvSet+=1

        polygons = mesh.polygons
        triangles = []
        triangleNormals = []
        for p in polygons:
            nal = numpy.asarray(p.normal)
            ni = len(triangleNormals)
            triangleNormals.append(' '.join(str(val) for val in nal))
            s = p.loop_start
            if(p.loop_total == 3):                             
                triangles.append( loops[s+0].vertex_index)
                triangles.append(ni)
                triangles.append( loops[s+1].vertex_index)
                triangles.append(ni)
                triangles.append( loops[s+2].vertex_index)
                triangles.append(ni)
            elif(p.loop_total == 4):
                triangles.append( loops[s+0].vertex_index)
                triangles.append(ni)
                triangles.append( loops[s+1].vertex_index)
                triangles.append(ni)
                triangles.append( loops[s+2].vertex_index)               
                triangles.append(ni)
                triangles.append( loops[s+0].vertex_index)
                triangles.append(ni)
                triangles.append( loops[s+2].vertex_index)
                triangles.append(ni)
                triangles.append( loops[s+3].vertex_index)
                triangles.append(ni)
            else:
                print('Plygon has to be triangles or quads...')
                
        sourceTriNormals = g + '.triangle.normals'
        sourceTriNormalsData = ' '.join( str for str in triangleNormals)

        geometry = ET.SubElement(lib_geometries, 'geometry')
        geometry.set('id', g)
        meshDom = ET.SubElement(geometry, 'mesh')        
        buildSource(meshDom, vertStrData, len(vertices) * 3, sourceNamePos,
            [ Param('x',DataType.float), Param('y',DataType.float), Param('z',DataType.float) ], SourceType.float_array)     
        for i in range(len(allUVCoords)):
            uvCoord = allUVCoords[i]
            datum = ' '.join( str for str in uvCoord )
            buildSource(meshDom, datum, len(allUVCoords[i]) * 2, allUVCoordsName[i],
                [ Param('u',DataType.float), Param('v',DataType.float)], SourceType.float_array)
        buildSource(meshDom, sourceTriNormalsData, len(triangleNormals) * 3, sourceTriNormals, 
            [ Param('x',DataType.float), Param('y',DataType.float), Param('z',DataType.float) ], SourceType.float_array)
        
        verticesDom = ET.SubElement(meshDom, 'vertices')
        verticesDomID = g + '.vertices'
        verticesDom.set('id', verticesDomID)
        vertexPosInput = ET.SubElement(verticesDom, 'input')
        vertexPosInput.set('semantic', 'POSITION')
        vertexPosInput.set('source', '#' + sourceNamePos)
        for i in range(len(allUVCoords)):
            vertexTexCoordInput = ET.SubElement(verticesDom, 'input')
            vertexTexCoordInput.set('semantic', 'TEXCOORD' + str(i))
            vertexTexCoordInput.set('source', '#' + allUVCoordsName[i])
        
        trianglesDom = ET.SubElement(meshDom, 'triangles')
        trianglesDom.set('count', str(int(len(triangles)/3)))
        
        triangleInput = ET.SubElement(trianglesDom, 'input')
        triangleInput.set('semantic', 'VERTEX')
        triangleInput.set('source', '#' + verticesDomID)
        triangleInput.set('offset', '0')
        
        triangleInput = ET.SubElement(trianglesDom, 'input')
        triangleInput.set('semantic', 'NORMAL')
        triangleInput.set('source', '#' + sourceTriNormals)
        triangleInput.set('offset', '1')
        
        pData = ' '.join( str(v) for v in triangles)
        pDom = ET.SubElement(trianglesDom, 'p')
        pDom.text = pData
        
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

def buildAnimation( node, strip ):
    if(strip == None):
        return;
    action = strip.action
    actionIDRoot = action.id_root

    if(actionIDRoot == 'MESH'):
        #print('Handle fcurve in MESH mode')
        #1. pick up vertices that changes in the clip.
        #2. build source, channel, sampler for each such vertex.
        fcurves = action.fcurves
        print('Build sources and channels for vertices ' + str(len(fcurves)))
        print('Removing dead vertex is required.')
    elif (actionIDRoot == 'OBJECT'):
        groups = action.groups
        for grp in groups:
            chs = grp.channels
            timelineset = set()
            for ch in chs:
                kfpts = ch.keyframe_points
                for kf in kfpts:
                    timelineset.add(kf.co[0])
            timeline = list(timelineset)
            timeline.sort()
            
            transMats = []
            interpolation = []
            for timePt in timeline:
                translate = []
                quaternion = []
                scaling = []
                for ch in chs:
                    type = ch.data_path.split('.')[-1]
                    if( type == 'location'):
                        translate.append(ch.evaluate(timePt))
                    elif( type == 'rotation_quaternion'):
                        quaternion.append(ch.evaluate(timePt))
                    elif( type == 'scale'):
                        scaling.append(ch.evaluate(timePt))
                matLoc = Matrix.Identity(4) if len(translate) != 3 else Matrix.Translation( ( translate[0], translate[1], translate[2]) )
                matRot = Matrix.Identity(4) if len(quaternion) != 4 else Quaternion( (quaternion[0], quaternion[1], quaternion[2], quaternion[3]) ).to_matrix().to_4x4()
                matScl = Matrix.Identity(4)
                if( len(scaling) == 3):
                    matScl[0][0] = scaling[0]
                    matScl[1][1] = scaling[1]
                    matScl[2][2] = scaling[2]
                    
                mat =  matRot * matScl * matLoc
                matStrs = matrixToStrList(mat, True)
                transMats.append(matStrs)
                interpolation.append('LINEAR')
            timelineDatumName = grp.name + '.timeline'
            datumTimeline = ' '.join(str(v) for v in timeline)
            buildSource(node, datumTimeline, len(timeline), timelineDatumName,
                [ Param('TIME',DataType.float) ], SourceType.float_array)
                
            transformName = grp.name + '.transform'
            datumTransform = ' '.join( v for v in transMats )
            buildSource(node, datumTransform, len(transMats) * 16, transformName,
                [ Param('TRANSFORM',DataType.float4x4) ], SourceType.float_array)
                
            interpoName = grp.name + '.interpolation'
            datumInterpo = ' '.join( v for v in interpolation )
            buildSource(node, datumInterpo, len(interpolation), interpoName,
                [ Param('INTERPOLATION',DataType.string) ], SourceType.Name_array)
            
            samplerID = grp.name + '.sampler'
            sampler = ET.SubElement(node, 'sampler')
            sampler.set('id', samplerID)
            addInputBlock(sampler, 'INPUT', '#' + timelineDatumName)
            addInputBlock(sampler, 'OUTPUT', '#' + transformName)
            addInputBlock(sampler, 'INTERPOLATION', '#' + interpoName)
            
            channel = ET.SubElement(node, 'channel')
            channel.set('source', '#' + samplerID)
            channel.set('target', grp.name + '/transform')

# DO NOT Support MESH animation yet.
# ONLY support linear matrix interpolation for smaller file size.              
def loadLibAnimations(lib_animations):
    objscene = bpy.data.scenes[0]
    objs = objscene.objects
    for obj in objs:
        obj.update_from_editmode()
        objName = obj.name
        objType = obj.type

        animData = None
        type = None
        if(objType == 'ARMATURE'):
            animData = obj.animation_data
        #elif(objType == 'MESH' and obj.data.animation_data != None ):
        #    animData = obj.data.animation_data
        if(animData != None):
            tracks = animData.nla_tracks
            for tra in tracks:                
                traNode = ET.SubElement(lib_animations, 'animation')
                traNode.set('id', objName + '.' + tra.name)
                strip = tra.strips[0]
                buildAnimation(traNode, strip)
            
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
    
    lib_animations = ET.SubElement(collada, 'library_animations')
    lib_geometries = ET.SubElement(collada, 'library_geometries')    
    lib_controllers = ET.SubElement(collada, 'library_controllers')
    lib_visual_sence = ET.SubElement(collada, 'library_visual_scenes')
    
    loadLibVisualScene(lib_visual_sence)
    loadLibGeometries(lib_geometries)
    loadLibControllers(lib_controllers)
    loadLibAnimations(lib_animations)
    
    prettify(collada)
    tree = ET.ElementTree(collada)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)
    
#### comment this test output part when deploying. ####
#export(bpy.context, r'D://projects//dae_library//assets//dae_dev_mesh.dae')
