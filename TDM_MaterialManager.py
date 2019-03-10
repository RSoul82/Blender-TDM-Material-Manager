import bpy
import os
import re
import json
import zipfile

class TDMPanel(bpy.types.Panel):
    bl_idname = "TDM_MM_PT_tdm_material_manager"
    bl_space_type = "VIEW_3D"
    bl_context = "objectmode"
    bl_region_type = "UI"
    bl_label = "TDM Material Manager"
    bl_category = "TDM"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        layout.row().operator('object.set_tdm_mats', icon = 'MATERIAL')
        layout.row().operator('object.load_tdm_texures', icon = 'TEXTURE')
        
        layout.row().separator()
        layout.row().label(text="Setup")
        
        rowTDMDir = layout.row()
        colTDMDir = rowTDMDir.column(align=True)
        colTDMDir.label(text="TDM Installation Folder")
        colTDMDir.prop(context.scene, 'tdmFolder')
        
        row3 = layout.row()
        col3 = row3.column(align = True)
        col3.label(text="TDM .mtr Files Location")
        col3.prop(context.scene, 'matPathTDM')
        col3.label(text="Custom .mtr Files Location (optional)")
        col3.prop(context.scene, 'matPathFM')
        
        col3.label(text="TDM Extracted Textures Location")
        col3.prop(context.scene, 'texPathTDM')
        col3.label(text="Custom Extracted Textures Location (optional)")
        col3.prop(context.scene, 'texPathFM')
        
        layout.row().operator('object.extract_textures', icon = 'FILE_IMAGE')
        
        layout.row().operator('object.extract_materials', icon = 'FILE_SCRIPT')
        
        col3.separator()
        
        layout.row().operator('object.save_settings', icon = 'FILE_TICK')
        
class ExtractMaterials(bpy.types.Operator):
    """Extracts all the .mtr files from TDM's pk4 files."""
    bl_idname = 'object.extract_materials'
    bl_label = 'Extract MTR Files'
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        dirTDM = pathToAbs(context.scene.tdmFolder)
        matDirTDM = pathToAbs(context.scene.matPathTDM)
        
        if os.path.exists(dirTDM):
            if not os.path.exists(matDirTDM):
                os.mkdir(matDirTDM)
            pk4Files = os.listdir(dirTDM)
            print('Extracting MTR files to ' + matDirTDM)
            for file in pk4Files:
                if file.lower().endswith('.pk4'):
                    zF = zipfile.ZipFile(os.path.join(dirTDM, file), 'r')
                    zContents = zF.namelist()
                    for zEntry in zContents:
                        if zEntry.lower().endswith('mtr'):
                            data = zF.read(zEntry) #get bytes
                            newFilePath = os.path.join(matDirTDM, os.path.basename(zEntry))
                            newFile = open(newFilePath, 'wb') #open file for writing the bytes of the object read from the zip file
                            newFile.write(data)
                            newFile.close()
                    zF.close()
            self.report({'INFO'}, 'Finished')
        else:
            self.report({'ERROR'}, 'Path not found: ' + dirTDM)
        return {'FINISHED'}
        
class ExtractTextures(bpy.types.Operator):
    """Extracts all the textures from TDM's pk4 files."""
    bl_idname = 'object.extract_textures'
    bl_label = 'Extract TDM Textures'
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        dirTDM = pathToAbs(context.scene.tdmFolder)
        texDirTDM = pathToAbs(context.scene.texPathTDM)
        
        if os.path.exists(dirTDM):
            self.report({'INFO'}, 'Please wait...')
            pk4Files = os.listdir(dirTDM)
            print('Extracting Textures to ' + texDirTDM)
            for file in pk4Files:
                if file.lower().endswith('.pk4'):
                    pathStart = 'dds/textures/darkmod/' #most textures start this way in the pk4 files
                    #alternate path start for models pk4 files
                    if file.lower().endswith('tdm_models01.pk4') or file.lower().endswith('tdm_models02.pk4'):
                        pathStart = 'dds/models/darkmod/'
                    elif file.lower().endswith('tdm_textures_sfx01.pk4'):
                        pathStart = 'textures/darkmod/'
                    elif file.lower().endswith('tdm_textures_base01.pk4'):
                        pathStart = 'textures/'
                    zF = zipfile.ZipFile(os.path.join(dirTDM, file), 'r')
                    zContents = zF.namelist()
                    extractFromRoot(zF, zContents, pathStart, texDirTDM) #extracts all texture files whose path starts with the specified string
                    #special case for decals pk4 which has files in two roots
                    if file.lower().endswith('tdm_textures_decals01.pk4'):
                        extractFromRoot(zF, zContents, 'textures/darkmod/', texDirTDM)
                    zF.close()
            self.report({'INFO'}, 'Finished')
        
        else:
            self.report({'ERROR'}, 'Path not found: ' + dirTDM)
        
        return {'FINISHED'}

def extractFromRoot(zipFile, zContents, pathStart, texDirTDM):
    for zEntry in zContents:
        if zEntry.startswith(pathStart) and not zEntry.endswith('.jpg'):
            data = zipFile.read(zEntry) #get bytes
            newFilePath = os.path.join(texDirTDM, zEntry.replace(pathStart, '')) #don't include dds/textures/darkmod/ in extracted file path
            newFilename = os.path.basename(newFilePath) #get the short filename
            newDirPath = newFilePath.replace(newFilename, '') #get the folder only by removing the short filename
            if not os.path.exists(newDirPath):
                os.makedirs(newDirPath)
            newFile = open(newFilePath, 'wb') #open file for writing the bytes of the object read from the zip file
            newFile.write(data)
            newFile.close()

class SetTDMMaterials(bpy.types.Operator):
    """Sets TDM material names based on assigned textures."""
    bl_idname = 'object.set_tdm_mats'
    bl_label = 'Set Material Names'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        texDirTDM = pathToAbs(context.scene.texPathTDM)
        matDirTDM = pathToAbs(context.scene.matPathTDM) #ensure path is absolute
        texDirFM = ''
        matDirFM = ''
        if context.scene.texPathFM != '':
            texDirFM = pathToAbs(context.scene.texPathFM)
        if context.scene.matPathFM != '':
            matDirFM = pathToAbs(context.scene.matPathFM)
        
        #get all paths that should exist
        pathList = setPathList(context, matDirTDM, texDirTDM, matDirFM, texDirFM)
        
        notFound = pathsNotFound(pathList)
        
        print('Setting TDM material names from textures.')
        
        if len(notFound) == 0:            
            #get materials that are on an object
            obMats = []
            for ob in bpy.data.objects:
                if ob.type == 'MESH' and ob.visible_get(): #if object is visible
                    for objMat in ob.material_slots:
                        obMats.append(objMat.name)

            for mat in bpy.data.materials: #for all materials in scene
                if not mat.get('NoChange') == 1.0:
                    if mat.name in obMats: #if scene material is on this object
                        for n in mat.node_tree.nodes:
                            if(n.name == "Image Texture"):
                                imgPath = pathToAbs(n.image.filepath)
                                matTexShort = ''
                                if texDirTDM in imgPath:
                                    matTexShort = imgPath.replace(texDirTDM, '') #texture as defined in mtr file
                                elif texDirFM in imgPath:
                                    matTexShort = imgPath.replace(texDirFM, '') #texture as define in mtr file
                                matTexValue = matTexShort.replace('\\', '/') #file always uses /
                                
                                #make list of all mtr files
                                matFound = [] #all materials that have this texture as the diffuse texture
                                mFilesTDM = os.listdir(matDirTDM) #only filenames
                                mFilesFM = []
                                if matDirFM != '' and not context.scene.matPathFM.startswith(';'):
                                    mFilesFM = os.listdir(matDirFM) #only filenames
                                
                                #use above lists to create list of full paths to all FM and TDM mtr files
                                mFiles = []
                                for mtrFM in mFilesFM:
                                    mFiles.append(os.path.join(matDirFM, mtrFM))
                                for mtrTDM in mFilesTDM:
                                    mFiles.append(os.path.join(matDirTDM, mtrTDM))
                                
                                for file in mFiles:
                                    fname, ext = os.path.splitext(file)
                                    if ext == '.mtr':
                                        #open file and look for texture
                                        #print("Trying to open " + file)
                                        with open(file, encoding="utf8", errors='ignore') as f:
                                            matFile = f.readlines()
                                            matFound += findMaterials(matTexValue, matFile)
                            
                                if len(matFound) != 0:
                                    #found = True
                                    #set material name
                                    if len(matFound) == 1:
                                        if len(matFound[0]) > 63:
                                            mat.name = 'Name too long! See custom properties.'
                                            mat['FullName'] = matFound[0]
                                        else:
                                            mat.name = matFound[0]
                                    elif len(matFound) > 1:
                                        if 'textures/common/shadow' in matFound:
                                            mat.name = 'textures/common/shadow'
                                            self.report({'WARNING'}, 'Shadow texture found. Material name assumed to be textures/common/shadow. If this is wrong, set the name manually and use the NoChange custom property to keep it.')
                                        else:
                                            mat.name = 'Multiple found. See Custom Properties.'
                                            self.report({'WARNING'}, 'Multiple materials found for ' + matTexValue + '. Copy correct name from custom properties, set name manually and use the NoChange custom property to keep it.')
                                            mCount = 0
                                            for found in matFound:
                                                numStr = str(mCount + 1)
                                                mat['Material ' + numStr.zfill(2)] = found #add each material to a custom property.
                                                mCount += 1
        else:
            for path in notFound:
                self.report({'ERROR'}, 'Path not found: ' + path)
    
        return {'FINISHED'}

#starts where the diffuse texture is found and then goes backwards until all material lines are found
def findMaterials(texturePath, fileLines):
    foundMats = [] #all materials with this texture as the diffuse map
    #remove extension from filename
    if '.dds' in texturePath:
        texturePath = texturePath.replace('.dds', '')
    elif '.tga' in texturePath:
        texturePath = texturePath.replace('.tga', '')

    for i in range(len(fileLines)):
        if texturePath in fileLines[i]:
            materialName = matSearch(i, fileLines)
            if materialName != '' and materialName not in foundMats:
                foundMats.append(materialName) #when a line is found matching the texture name, matSearch will go back to the material name
    return foundMats

#start where the texture was and go backwards until the material is found
def matSearch(index, fileLines):
    matFound = '' #default value
    for i in range(index, -1, -1):
        if materialLineFound(fileLines[i]):
            matLine = fileLines[i] #this should be split by whitespace
            matSplit = re.split(' |\t', matLine)
            matFound = matSplit[0].strip()
            break
    return matFound

#true if line begins with a valid material name
def materialLineFound(lineText):
    notThese = { '', ' ', '\t', '{', '}', '/', '\r', '\n'} #line should not start with these things to be a valid material line
    #does not work properly - see lights.mtr for an example
    if len(lineText) != 0:
        if lineText[0] not in notThese:
            return True
        else:
            return False
    else:
        return False

class LoadTDMTextures(bpy.types.Operator):
    """Loads TDM textures based on material names. Collision materials are made partially transparent."""
    bl_idname = 'object.load_tdm_texures'
    bl_label = 'Load Textures'
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        tex_dir_user = context.scene.texPathTDM
        texDirTDM = pathToAbs(tex_dir_user) #ensure path is absolute
        matDirTDM = pathToAbs(context.scene.matPathTDM) #ensure path is absolute
        
        texDirFM = ''
        matDirFM = ''
        if context.scene.texPathFM != '':
            texDirFM = pathToAbs(context.scene.texPathFM)
        if context.scene.matPathFM != '':
            matDirFM = pathToAbs(context.scene.matPathFM)
        
        #get all paths that should exist
        pathList = setPathList(context, matDirTDM, texDirTDM, matDirFM, texDirFM)
        
        notFound = pathsNotFound(pathList)
        
        if len(notFound) == 0:
            print('Loading textures')
            
            for ob in bpy.data.objects:
                if ob.type == 'MESH' and ob.hide == 0: #if object is a mesh and visible (rules out lamps etc)
                    #make list of all mtr files
                    mFilesTDM = os.listdir(matDirTDM) #only filenames
                    mFilesFM = []
                    if matDirFM != '' and not context.scene.matPathFM.startswith(';'):
                        mFilesFM = os.listdir(matDirFM) #only filenames
                    
                    #use above lists to create list of full paths to all FM and TDM mtr files
                    mFiles = []
                    for mtrFM in mFilesFM:
                        mFiles.append(os.path.join(matDirFM, mtrFM))
                    for mtrTDM in mFilesTDM:
                        mFiles.append(os.path.join(matDirTDM, mtrTDM))
                    
                    for objMat in ob.material_slots:
                        mName = objMat.name
                        #for each mtr file, look for mName
                        mat = bpy.data.materials[mName]
                        textureFound = '' #default value, filled in if diffuse texture is found
                        for file in mFiles:
                            fname, ext = os.path.splitext(file)
                            if ext.lower() == '.mtr':
                                #open file and look for material
                                with open(file, encoding="utf8", errors='ignore') as f:
                                    matFile = f.readlines()
                                    
                                    #first, look for texture in the user's FM dir
                                    textureFound = findDiffuse(texDirFM, mName, matFile, False)
                                    if textureFound == '':
                                        #if not found, look in original TDM textures dir
                                        textureFound = findDiffuse(texDirTDM, mName, matFile, True)
                                    
                                    if textureFound != '':
                                        break
                                
                        if textureFound != '':
                            texIndex = getTexIndex(textureFound.strip())
                            #assign texture to material
                            #if image is already loaded, use it, or load it as a new image
                            if texIndex != -1:
                                img = bpy.data.images[texIndex]
                            else:
                                img = bpy.data.images.load(textureFound.strip()) #file lines end with \n
                            
                            mTexSlot = mat.texture_slots[0] #only work with the first texture slot
                            if(mTexSlot == None):
                                tex = bpy.data.textures.new('Tex', 'IMAGE')
                                tex.image = img
                                mtex = mat.texture_slots.add()
                                mtex.texture = tex
                            else:
                                if hasattr(mTexSlot, 'filepath'):
                                    mTexSlot.texture.image.filepath = textureFound.strip()
                                else:
                                    tex = bpy.data.textures.new('Tex', 'IMAGE')
                                    tex.image = img
                                    mTexSlot.texture = tex
                                    mTexSlot.texture.image.filepath = textureFound.strip()
        else:
            for path in notFound:
                self.report({'ERROR'}, 'Path not found: ' + path)
        
        return {'FINISHED'}

#returns a list of paths that which ought to exist (FM paths not blank, and do not start with ;)
def setPathList(context, matDirTDM, texDirTDM, matDirFM, texDirFM):
    pathList = { matDirTDM, texDirTDM }
    if texDirFM != '' and not context.scene.texPathFM.startswith(';'):
        pathList.add(texDirFM)
        
    if matDirFM != '' and not context.scene.matPathFM.startswith(';'):
        pathList.add(matDirFM)
    return pathList

def pathsNotFound(pathList):
    notFound = []
    for path in pathList:
        if path != '':
            if not os.path.exists(path):
                notFound.append(path)
    return notFound

#searches through all the lines of an mtr file and returns whatever diffuse texture is found
def findDiffuse(tex_dir, materialName, fileLines, lastChance):
    if materialName.startswith('tdm_collision_') or materialName == 'textures/common/collision':
        collisionMat = True
    else:
        collisionMat = False
    if materialName == 'textures/common/shadow':
        shadowMat = True
    else:
        shadowMat = False
    textureFound = ''
    for i in range(len(fileLines)):
        #spMatLine = re.split(' |\t', fileLines[i]) #splits by spaces and tabs
        matLine0 = fileLines[i].strip()
        if matLine0 == materialName:
        #if spMatLine[0] == materialName:
            bracketCount = 0 #keeps track of code blocks by counting {s minus }s
            while True:
                matLine = fileLines[i+1].strip()
                if matLine.startswith('{'):
                    bracketCount = bracketCount + 1
                elif matLine.startswith('}'):
                    bracketCount = bracketCount - 1
                
                if diffuseTextureDefined(matLine, collisionMat, shadowMat):
                    splitLine = re.split(' |\t', matLine) #splits by spaces and tabs
                    for text in splitLine:
                        trimmed = text.strip()
                        texStartLocation = getTexNameLocation(trimmed)
                        texName = trimmed[texStartLocation:] #gets everything to the right of darkmod
                        texPath = os.path.join(tex_dir, texName)
                        textureFound = os.path.normpath(texPath) #for \ or / consistency
                        #remove any extensions that may be found
                        if textureFound.endswith('.dds') or textureFound.endswith('tga'):
                            textureFound = os.path.splitext(textureFound)[0]
                        bracketCount = 0 #forces the current iteration to stop once a texture has been found
                
                i = i + 1
                if bracketCount == 0:
                    break
    if os.path.exists(textureFound + '.dds'): #look for dds extension first
        return textureFound + '.dds'
    elif os.path.exists(textureFound + '.tga'):
        return textureFound + '.tga'
    else:
        if lastChance and textureFound != '':
            print('Warning: Texture not found: ' + textureFound + ' for material: ' + materialName)
        return ''

#gets the index of the start of the texture path
def getTexNameLocation(fileLine):
    if fileLine.startswith('textures/darkmod') or fileLine.startswith('models/darkmod'):
        return fileLine.find('darkmod') + len('darkmod') + 1
    elif fileLine.startswith('textures/common'):
        return fileLine.find('textures') + len('textures') + 1
    

#Get the index of the first existing image slot whose filepath matches the image to be loaded. -1 if image not already loaded.
def getTexIndex(texturePath):
        index = -1
        for img in range(len(bpy.data.images)):
            if bpy.data.images[img].filepath == texturePath.strip():
                index = img
                break
        return index

#true if diffuse texture specified
def diffuseTextureDefined(lineText, collisionMat, shadowMat):
    if lineText.startswith('diffusemap'):
        return True
    elif lineText.startswith('map'):
        return True
    elif collisionMat or shadowMat:
        if lineText.startswith('qer_editorimage'): #last resort, should only happen with collision materials
            return True
    else:
        return False

#Ensures a path is absolute rather than relative
def pathToAbs(pathToSet):
    if pathToSet != '':
        return os.path.abspath(bpy.path.abspath(pathToSet))
    else:
        return ''

config_filename = 'TDM_Material_Manager_Config.txt'
config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
config_filepath = os.path.join(config_path, config_filename)

default_config = {'TDMFolder': '...', 'mtrLocationTDM': '...', 'mtrLocationFM': '', 'texLocationTDM': '...', 'texLocationFM': ''}

class SaveSettings(bpy.types.Operator):
    """Save Locations for future uses"""
    bl_idname = 'object.save_settings'
    bl_label = 'Save Folder Locations'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        config_file = open(config_filepath, 'w')
        new_config = { 'TDMFolder' : context.scene.tdmFolder, 'texLocationTDM' : context.scene.texPathTDM, 'texLocationFM' : context.scene.texPathFM, 'mtrLocationTDM' : context.scene.matPathTDM, 'mtrLocationFM' : context.scene.matPathFM }
        json.dump(new_config, config_file, indent=4, sort_keys=True)
        config_file.close()
        
        self.report({'INFO'}, 'Blender must be restarted for updated paths to used for new objects.')
        
        return {'FINISHED'}

classes = (TDMPanel, SetTDMMaterials, LoadTDMTextures, SaveSettings, ExtractTextures, ExtractMaterials)

def register():
    print('----- Registering TDM Material Manager. -----')
    for cls in classes:
        bpy.utils.register_class(cls)
    
    #try to load config file
    try:
        config_file = open(config_filepath, 'r')
        config_from_file = json.load(config_file)
    except IOError:
        config_file = open(config_filepath, 'w')
        json.dump(default_config, config_file, indent=4, sort_keys=True)
        config_file.close()
        config_file = open(config_filepath, 'r')
        config_from_file = json.load(config_file)
        config_file.close()
    
    #define user properties
    bpy.types.Scene.tdmFolder = bpy.props.StringProperty(name='', description = 'Path to your TDM installation folder.', default=tryConfig('TDMFolder', config_from_file))
    bpy.types.Scene.matPathTDM = bpy.props.StringProperty(name='', description = '.mtr files that come with TDM\'s .pk4 files.', default=tryConfig('mtrLocationTDM', config_from_file))
    bpy.types.Scene.matPathFM = bpy.props.StringProperty(name='', description = '(Optional) custom .mtr files for your FM.', default=tryConfig('mtrLocationFM', config_from_file)) 
    bpy.types.Scene.texPathTDM = bpy.props.StringProperty(name='', description = 'texture files that come with TDM\'s .pk4 files.', default=tryConfig('texLocationTDM', config_from_file))
    bpy.types.Scene.texPathFM = bpy.props.StringProperty(name='', description = '(Optional) custom texture files for your FM.', default=tryConfig('texLocationFM', config_from_file))
    
    print('----- Registration Complete. -----')

#Try to get a value from a config file. Return ... if key not founnd.
def tryConfig(key, config_from_file):
    try:
        return config_from_file[key]
    except:
        return '...'

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()