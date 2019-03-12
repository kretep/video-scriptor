import os
import numpy as np
import imageio
import yaml
import random
from scipy.ndimage.interpolation import affine_transform

class AniMeta:
    def __init__(self, x0, y0, s0, x1, y1, s1):
        self.x0 = x0
        self.y0 = y0
        self.s0 = s0
        self.x1 = x1
        self.y1 = y1
        self.s1 = s1

def getRandomAnimationPoint(npIm, fake):
    scale = 1.0 + 0.2 * random.random()
    fx = random.random()
    fy = random.random()

    originalWidth = npIm.shape[1]
    originalHeight = npIm.shape[0]
    targetWidth = 1440
    targetHeight = 1080

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
def animateImage2(npIm, animeta, i, totalDuration, framerate):
    
    # Interpolate
    t = i / (totalDuration * framerate)
    dx = animeta.x0 * (1.0 - t) + animeta.x1 * t
    dy = animeta.y0 * (1.0 - t) + animeta.y1 * t
    s =  animeta.s0 * (1.0 - t) + animeta.s1 * t

    # Apply transformation matrix and offset
    matrix = [[ s, 0, 0],
              [ 0, s, 0],
              [ 0, 0, 1]]
    offset = [dy, dx, 0] # y before x!
    print (dx, dy, s)
    return affine_transform(npIm, matrix, offset, (1080, 1440, 3),
        order=1, mode='constant', cval=255.0)

with open('video.spec.yml') as t:
    script = yaml.safe_load(t)
    print(script)
    writer = imageio.get_writer(os.path.join('output', 'video_imageio.mp4'), fps=30)

    framerate = script['framerate']

    npPrevImage = None #todo: make empty/black image
    prevAnimeta = None
    prevDuration = 0

    # Process images in script
    images = script['images']
    k = 0
    for image in images:
        
        # Read image
        npImCurrent = imageio.imread('./input/%s' % image['file'])
        #print(npImCurrent.shape)
        if prevAnimeta == None: # cannot compare np array to None?
            npPrevImage = npImCurrent

        # Some administration for transition
        transition = image['transition']
        transitionDuration = 0
        transitionType = None
        if 'type' in transition and 'duration' in transition:
            transitionDuration = transition['duration']
            transitionType = transition['type']

        # Same for animation
        animation = image['animation']
        animationType = None
        animeta = None
        if 'type' in animation:
            animationType = animation['type']
            animeta = AniMeta(*getRandomAnimationPoint(npImCurrent, 0), *getRandomAnimationPoint(npImCurrent, 1))
            print("Animation: ", animeta.x0, animeta.y0, animeta.s0, animeta.x1, animeta.y1, animeta.s1)

        # Generate frames
        duration = image['duration']
        nframes = int(duration * framerate)
        for i in range(0, nframes):
            print("processing %s frame %d" % (image['file'], i))

            # Animate image
            #TODO: use transitionDuration of NEXT image
            npIm1 = animateImage2(npImCurrent, animeta, i, duration + transitionDuration, framerate)
            
            # Transition
            transitionAlpha = 1.0 if (transitionDuration == 0) else i / (transitionDuration * framerate)
            if transitionAlpha < 1.0:
                # Animate previous image
                npIm0 = animateImage2(npPrevImage, prevAnimeta, prevDuration * framerate + i, 
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

        npPrevImage = npImCurrent
        prevAnimeta = animeta
        prevDuration = duration

    writer.close()
