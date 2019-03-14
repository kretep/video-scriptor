import random
from scipy.ndimage.interpolation import affine_transform
from properties import Props

class PanZoomAnimation:
    def __init__(self, npIm, spec):
        self.npIm = npIm
        self.frameWidth = spec.getRootValue(Props.FRAME_WIDTH)
        self.frameHeight = spec.getRootValue(Props.FRAME_HEIGHT)
        (self.x0, self.y0, self.s0) = \
            self.getRandomAnimationPoint(spec.get('x0'), spec.get('y0'), spec.get('s0'))
        (self.x1, self.y1, self.s1) = \
            self.getRandomAnimationPoint(spec.get('x1'), spec.get('y1'), spec.get('s1'))
        print(self.x0, self.y0, self.s0, self.x1, self.y1, self.s1)

    def getRandomAnimationPoint(self, fx, fy, fs):
        scale = 1.0 + 0.2 * random.random() if fs == None else fs
        fx = random.random() if fx == None else fx
        fy = random.random() if fy == None else fy

        originalWidth = self.npIm.shape[1]
        originalHeight = self.npIm.shape[0]

        # The actual frame scale used
        frameScaleW = 1.0 * self.frameWidth / originalWidth

        # When the aspect ratio of the image doesn't match that of the target frame,
        # we want to know the covered height so the animation potentially covers the
        # full height
        originalHeightCovered = self.frameHeight / frameScaleW

        dx = fx * (originalWidth - (originalWidth / scale))
        dy = fy * (originalHeight - (originalHeightCovered / scale))
        combinedScale = 1 / (scale * frameScaleW)
        return (dx, dy, combinedScale)

    def animate(self, t):
        
        # Interpolate
        dx = self.x0 * (1.0 - t) + self.x1 * t
        dy = self.y0 * (1.0 - t) + self.y1 * t
        s =  self.s0 * (1.0 - t) + self.s1 * t

        # Apply transformation matrix and offset
        matrix = [[ s, 0, 0],
                  [ 0, s, 0],
                  [ 0, 0, 1]]
        offset = [dy, dx, 0] # y before x!
        print (dx, dy, s)
        outputShape = (self.frameHeight, self.frameWidth, 3) # height before width!
        return affine_transform(self.npIm, matrix, offset, outputShape,
            order=1, mode='constant', cval=255.0)
