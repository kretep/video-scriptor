import random
from scipy.ndimage.interpolation import affine_transform
maxScale = 1.1

class PanZoomAnimation:

    def __init__(self, npIm, spec):
        self.npIm = npIm
        self.frameWidth = spec.getRootValue('framewidth', 1440)
        self.frameHeight = spec.getRootValue('frameheight', 1080)
        self.interpolationOrder = spec.get('interpolationorder', 1)

        # Preset
        self.animationPreset = spec.get('animation-preset', None)
        (x0, y0, s0, x1, y1, s1) = 6 * [None]
        if not self.animationPreset is None:
            presets = {
                'top-bottom': (0.5, 0.0, maxScale, 0.5, 1.0, maxScale),
                'bottom-top': (0.5, 1.0, maxScale, 0.5, 0.0, maxScale),
                'left-right': (0.0, 0.5, maxScale, 1.0, 0.5, maxScale),
                'right-left': (1.0, 0.5, maxScale, 0.0, 0.5, maxScale),
                'zoom-in-center': (0.5, 0.5, 1.0, 0.5, 0.5, maxScale),
                'zoom-out-center': (0.5, 0.5, maxScale, 0.5, 0.5, 1.0)
            }
            (x0, y0, s0, x1, y1, s1) = presets[self.animationPreset]

        # Override preset / default
        (x0, y0, s0) = (spec.get('x0', x0), spec.get('y0', y0), spec.get('s0', s0))
        (x1, y1, s1) = (spec.get('x1', x1), spec.get('y1', y1), spec.get('s1', s1))

        # Generate animation points and scale to bounds
        (self.x0, self.y0, self.s0) = self.getRandomAnimationPoint(x0, y0, s0)
        (self.x1, self.y1, self.s1) = self.getRandomAnimationPoint(x1, y1, s1)
        print(self.x0, self.y0, self.s0, self.x1, self.y1, self.s1)

    def getRandomAnimationPoint(self, fx, fy, fs):
        r = (random.random(), random.random(), random.random()) # always generate, even if not using
        scale = 1.0 + (maxScale - 1.0) * r[0] if fs == None else fs
        fx = r[1] if fx == None else fx
        fy = r[2] if fy == None else fy
        # TODO: limit y-range in wide-screen
        # fy = 0.8 * fy + 0.1

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
        outputShape = (self.frameHeight, self.frameWidth, 3) # height before width!
        return affine_transform(self.npIm, matrix, offset, outputShape,
            order=self.interpolationOrder, mode='constant', cval=255.0)
        