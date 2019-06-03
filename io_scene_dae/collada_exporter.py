import bpy
import numpy
import mathutils
from enum import Enum
from mathutils import Matrix, Quaternion, Vector
import xml.etree.ElementTree as ET

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
        matText = matrixToStrList(cb.matrix_basis.copy(), True)
        matrix.text = matText
                
        for c in cb.children:
            dc = ET.SubElement(dom, 'node')
            boneStack.append(c)
            domStack.append(dc)
    
def loadNodeArmature(obj, domNode):
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
         
        bones = obj.pose.bones
        sourceName_0 = c + '.joints'
        bonesNameList = ' '.join( b.name for b in bones )
                
        boneMats = []
        for b in bones:
            boneMatrix = b.matrix.copy()
            boneMatrix.inverted()
            boneMats.append(matrixToStrList(boneMatrix, True))   
        sourceName_1 = c + '.inverse.bind.matrix'
        boneMatrixList = ' '.join( str for str in boneMats )
 
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
            
        ctrl = ET.SubElement(lib_controllers, 'controller')
        ctrl.set('id', c)
        ctrl.set('name', obj.name)
        
        skin = ET.SubElement(ctrl, 'skin')
        skin.set('source', '#' + mesh.name)
        
        bsmat = ET.SubElement(skin, 'bind_shape_matrix')
        bsmat.text = matrixToStrList(obj.matrix_world.copy(), True)
        
        buildSource(skin, bonesNameList, len(bones), sourceName_0, [ Param('JOINT',DataType.string) ], SourceType.Name_array)
        buildSource(skin, boneMatrixList, len(bones) * 16, sourceName_1, [Param('TRANSFORM',DataType.float4x4)], SourceType.float_array)
        buildSource(skin, weightsStr, len(weights), sourceName_2, [Param('WEIGHT',DataType.float)], SourceType.float_array)
         
        joints = ET.SubElement(skin, 'joints')
        addInputBlock(joints, 'JOINT', '#' + sourceName_0)
        addInputBlock(joints, 'INV_BIND_MATRIX', '#' + sourceName_1)       
        
        vertexWeightDom = ET.SubElement(skin, 'vertex_weights')
        vertexWeightDom.set('count', str(len(vcount)))
        addInputBlock(vertexWeightDom, 'JOINT', '#' + sourceName_0, 0)
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
                mat = Quaternion( (chs[3].evaluate(timePt), chs[4].evaluate(timePt), chs[5].evaluate(timePt),  chs[6].evaluate(timePt)) ).to_matrix().to_4x4()
                translateMat = Matrix.Translation( Vector( (chs[0].evaluate(timePt), chs[1].evaluate(timePt), chs[2].evaluate(timePt)) ) )
                scaleMat = Matrix.Scale(1.0, 4, Vector( (chs[7].evaluate(timePt), chs[8].evaluate(timePt), chs[9].evaluate(timePt)) ) )
                mat = mat * translateMat * scaleMat
                matstrs = matrixToStrList(mat, True)
                transMats.append(matstrs)
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
        objName = obj.name
        objType = obj.type

        animData = None
        type = None
        if(objType == 'ARMATURE'):
            animData = obj.animation_data
        #elif(objType == 'MESH' and obj.data.animation_data != None ):
        #    animData = obj.data.animation_data
        if(animData != None):
            animNode = ET.SubElement(lib_animations, 'animation')
            animNode.set('id', objName)
            tracks = animData.nla_tracks
            for tra in tracks:                
                traNode = ET.SubElement(animNode, 'animation')
                traNode.set('id', tra.name)
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
export(bpy.context, r'D://projects//dae_library//assets//dev.dae')