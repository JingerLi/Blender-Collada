import xml.etree.ElementTree as ET

def prettify( root ):
    countstack = []
    elmstack = []
    elmstack.append(root)
    while len(elmstack) != 0:
        if(len(countstack) != 0):
            countstack[-1] -= 1
            if(countstack[-1] == 0):
                countstack.pop()
        p = elmstack.pop()
        if(len(p) == 0):
            p.tail = '\n' + len(countstack)*'\t'
        else:
            for c in reversed(p):
                elmstack.append(c)
            p.tail = '\n' + len(countstack) * '\t'
            countstack.append(len(p))
            p.text = '\n' + len(countstack) * '\t'

def export( context, filepath ):
    collada = ET.Element('COLLADA')
    collada.set('xmlns', 'http://www.collada.org/2005/11/COLLADASchema')
    collada.set('version', '1.5.0')
    collada.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    
    lib_geometries = ET.SubElement(collada, 'library_geometries')    
    lib_animations = ET.SubElement(collada, 'library_animations')
    lib_controllers = ET.SubElement(collada, 'library_controllers')
    lib_visual_sence = ET.SubElement(collada, 'library_visual_scenes')
    
    prettify(collada)
    tree = ET.ElementTree(collada)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)