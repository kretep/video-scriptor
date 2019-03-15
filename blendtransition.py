

class BlendTransition:

  def processTransition(self, npIm0, npIm1, transitionT):
    npResult = ((1.0 - transitionT) * npIm0 + transitionT * npIm1).astype('uint8')
    return npResult
