
class Spec:

    def __init__(self, specDict, parentSpec):
        self.specDict = specDict
        self.parentSpec = parentSpec
        self.nextSpec = None
        self.resultHolder = None

    def get(self, key, default=None, doRecurse=True):
        """Returns the value of the specified property in the current spec,
           or looks it up recursively in the parent spec when it is not found,
           or returns the property default if no match is found.
        """
        if key in self.specDict:
            return self.specDict[key]
        if self.parentSpec != None and doRecurse:
            return self.parentSpec.get(key, default)
        return default
    
    def getSpec(self, key, default=None, doRecurse=True):
        dict = self.get(key, default, doRecurse)
        return Spec(dict, self) if dict != None else None
    
    def getRootValue(self, key, default):
        """Returns the value of the specified property in the root spec,
           or returns the property default if no match is found.
        """
        if self.parentSpec == None:
            return self.specDict.get(key, default)
        return self.parentSpec.getRootValue(key, default)
