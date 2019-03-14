import random
from scipy.ndimage.interpolation import affine_transform
from properties import Props

class PanZoomAnimation:
    def __init__(self, npIm, spec):
        self.npIm = npIm
        self.frameWidth = spec.getRootValue(Props.FRAME_WIDTH)
        self.frameHeight = spec.getRootValue(Props.FRAME_HEIGHT)
        (x0, y0, s0) = self.getRandomAnimationPoint(0)
        (x1, y1, s1) = self.getRandomAnimationPoint(1)
        self.x0 = spec.get('x0', x0)
        self.y0 = spec.get('y0', y0)
        self.s0 = spec.get('s0', s0)
        self.x1 = spec.get('x1', x1)
        self.y1 = spec.get('y1', y1)
        self.s1 = spec.get('s1', s1)
        print(self.x0, self.y0, self.s0, self.x1, self.y1, self.s1)

    def getRandomAnimationPoint(self, fake):
        scale = 1.0 + 0.2 * random.random()
        fx = random.random()
        fy = random.random()

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
