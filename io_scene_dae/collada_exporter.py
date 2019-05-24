import xml.etree.ElementTree as ET

def loadLibGeometries( lib_geometries ):
    ET.SubElement(lib_geometries, 'mesh')
    print("TODO load geometries.")

def loadLibVisualScene( lib_visual_scene ):
    ET.SubElement(lib_visual_scene, 'node')
    print("TODO load visual scene.")

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
    
    prettify(collada)
    tree = ET.ElementTree(collada)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)