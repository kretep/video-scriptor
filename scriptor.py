import os
import numpy as np
import imageio
import yaml
import random
from scipy.ndimage.interpolation import affine_transform

class PanZoomAnimation:
    def __init__(self, npIm, rootSpec):
        self.npIm = npIm
        self.rootSpec = rootSpec
        (self.x0, self.y0, self.s0) = self.getRandomAnimationPoint(0)
        (self.x1, self.y1, self.s1) = self.getRandomAnimationPoint(1)

    def getRandomAnimationPoint(self, fake):
        scale = 1.0 + 0.2 * random.random()
        fx = random.random()
        fy = random.random()

        originalWidth = self.npIm.shape[1]
        originalHeight = self.npIm.shape[0]
        targetWidth = self.rootSpec['framewidth']
        targetHeight = self.rootSpec['frameheight']

        # The actual frame scale used
        frameScaleW = 1.0 * targetWidth / originalWidth

        # When the aspect ratio of the image doesn't match that of the target frame,
        # we want to know the covered height so the animation potentially covers the
        # full height
        originalHeightCovered = targetHeight / frameScaleW

        dx = fx * (originalWidth - (originalWidth / scale))
        dy = fy * (originalHeight - (originalHeightCovered / scale))
        combinedScale = 1 / (scale * frameScaleW)
        print(dx, dy, combinedScale)
        return (dx, dy, combinedScale)

    # totalDuration should include the animation duration for the current image and the
    # transition duration to the next image
    def animate(self, i, totalDuration, framerate):
        
        # Interpolate
        t = i / (totalDuration * framerate)
        dx = self.x0 * (1.0 - t) + self.x1 * t
        dy = self.y0 * (1.0 - t) + self.y1 * t
        s =  self.s0 * (1.0 - t) + self.s1 * t

        # Apply transformation matrix and offset
        matrix = [[ s, 0, 0],
                  [ 0, s, 0],
                  [ 0, 0, 1]]
        offset = [dy, dx, 0] # y before x!
        print (dx, dy, s)
        outputShape = (self.rootSpec['frameheight'], self.rootSpec['framewidth'], 3)
        return affine_transform(self.npIm, matrix, offset, outputShape,
            order=1, mode='constant', cval=255.0)

class Scriptor:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def generateVideo(self):
        with open('video.spec.yml') as t:
            script = yaml.safe_load(t)
            print(script)
            writer = imageio.get_writer(os.path.join('output', 'video_imageio.mp4'), fps=30)

            framerate = script['framerate']

            npImPrev = None #todo: make empty/black image
            prevAnimation = None
            prevDuration = 0

            # Process images in script
            images = script['images']
            k = 0
            for image in images:
                
                # Read image
                npImCurrent = imageio.imread('./input/%s' % image['file'])
                #print(npImCurrent.shape)
                if prevAnimation == None: # cannot compare np array to None?
                    npImPrev = npImCurrent

                # Some administration for transition
                transition = image['transition']
                transitionDuration = 0
                transitionType = None
                if 'type' in transition and 'duration' in transition:
                    transitionDuration = transition['duration']
                    transitionType = transition['type']

                # Same for animation
                animationSpec = image['animation']
                animationType = None
                animation = None
                if 'type' in animationSpec:
                    animationType = animationSpec['type']
                    animation = PanZoomAnimation(npImCurrent, script)

                # Generate frames
                duration = image['duration']
                nframes = int(duration * framerate)
                for i in range(0, nframes):
                    print("processing %s frame %d" % (image['file'], i))

                    # Animate image
                    #TODO: use transitionDuration of NEXT image
                    npIm1 = animation.animate(i, duration + transitionDuration, framerate)
                    
                    # Transition
                    transitionAlpha = 1.0 if (transitionDuration == 0) else i / (transitionDuration * framerate)
                    if transitionAlpha < 1.0:
                        # Animate previous image
                        npIm0 = prevAnimation.animate(prevDuration * framerate + i, 
                            prevDuration + transitionDuration, framerate)

                        # Combine transition images
                        npResult = ((1.0 - transitionAlpha) * npIm0 + transitionAlpha * npIm1).astype('uint8')
                    else:
                        npResult = npIm1

                    # Write result    
                    writer.append_data(npResult)

                    # Debugging
                    imageio.imwrite('./output/%04d.jpg' % k, npResult)
                    k += 1

                npImPrev = npImCurrent
                prevAnimation = animation
                prevDuration = duration

            writer.close()

if __name__ == "__main__":
    scriptor = Scriptor()
    scriptor.generateVideo()
