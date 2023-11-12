import glob
import xml.etree.ElementTree as ET
import json
views = glob.glob("**/*.xml",recursive=True)
for view in views:
    
    file = ET.parse(view)
    root = file.getroot()
    attrs_fields =root.findall(".//*[@attrs]")
    attrs_extend_parent_fields = root.findall(".//attribute[@name='attrs']/..")
    if attrs_extend_parent_fields:
        print(view)
        for parent in attrs_extend_parent_fields:
            attrs_extend_fields = parent.findall(".//attribute[@name='attrs']")
           
            for attrs_extend_element in attrs_extend_fields:
               
                attr_content = eval(attrs_extend_element.text.strip())
                
                for attr in attr_content:
                    value=attr_content[attr]
                    
                    element = ET.SubElement(parent, 'attribute')
                    element.set("name",attr)

                    element.text = str(value)
                attrs_extend_element.text
                parent.remove(attrs_extend_element)


        string = ET.tostring(root).decode('utf-8')
        file = open(view,"w")
        file.write(string)
        file.close()
        
       # break;
    #exit    
    
    if attrs_fields:
        for field in attrs_fields:
            attrs = field.attrib.get('attrs')
            attrib_list = eval(attrs)
            for attr in attrib_list:
                value=attrib_list[attr]
                field.set(attr,str(value))
                #print(value)
            del field.attrib['attrs']
        print(view)
        string = ET.tostring(root).decode('utf-8')
        file = open(view,"w")
        file.write(string)
        file.close()
        
        #break
        
            
           
            #print(attrib_list)
            