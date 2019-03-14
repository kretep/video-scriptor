
class Property:
    def __init__(self, key, default):
        self.key = key
        self.default = default
        
class Props:
    FRAME_RATE = Property('framerate', 30)
    FRAME_WIDTH = Property('framewidth', 1440)
    FRAME_HEIGHT = Property('frameheight', 1080)
    OUTPUT_FRAMES = Property('outputframes', '')
    OUTPUT_FILE = Property('outputfile', 'video.mp4')
    IMAGES = Property('images', [])

    IMAGE_FILE = Property('file', '')
    IMAGE_ANIMATION = Property('animation', {'type': 'panzoom'})
    IMAGE_ANIMATION_TYPE = Property('type', 'panzoom')

class Spec:

    def __init__(self, specDict, parentSpec):
        self.specDict = specDict
        self.parentSpec = parentSpec

    def get(self, propertyOrKey, default=None, doRecurse=True):
        """Returns the value of the specified property in the current spec,
           or looks it up recursively in the parent spec when it is not found,
           or returns the property default if no match is found.
        """
        property = Property(propertyOrKey, default) if isinstance(propertyOrKey, str) else propertyOrKey
        if property.key in self.specDict:
            return self.specDict[property.key]
        if self.parentSpec != None and doRecurse:
            return self.parentSpec.get(property)
        return property.default
    
    def getRootValue(self, property):
        """Returns the value of the specified property in the root spec,
           or returns the property default if no match is found.
        """
        if self.parentSpec != None:
            return self.parentSpec.getRootValue(property)
        return self.specDict.get(property.key, property.default)
