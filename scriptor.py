import os
import numpy as np
import imageio
import yaml
from panzoomanimation import PanZoomAnimation
from properties import Spec, Props
class Scriptor:

    def generateVideo(self):
        with open('video.spec.yml') as t:
            scriptDict = yaml.safe_load(t)
            spec = Spec(scriptDict, None)
            framerate = spec.get(Props.FRAME_RATE)
            outputFrames = spec.get(Props.OUTPUT_FRAMES)

            # Initialize writer
            filename = spec.get(Props.OUTPUT_FILE)
            writer = imageio.get_writer(os.path.join('output', filename), fps=framerate)

            prevAnimation = None
            prevDuration = 0

            # Process images in script
            globalFrameN = 0
            images = spec.get(Props.IMAGES)
            for image in images: # TODO: make spec.get return arry of Spec instead of array of dicts
                imageSpec = Spec(image, spec)

                # Read image
                inputFileName = imageSpec.get(Props.IMAGE_FILE)
                npImCurrent = imageio.imread('./input/%s' % inputFileName)
                
                # Some administration for transition
                transition = image['transition']
                transitionDuration = 0
                transitionType = None
                if 'type' in transition and 'duration' in transition:
                    transitionDuration = transition['duration']
                    transitionType = transition['type']

                # Same for animation
                animationSpecDict = imageSpec.get(Props.IMAGE_ANIMATION)
                animationSpec = Spec(animationSpecDict, imageSpec)
                animationType = animationSpec.get(Props.IMAGE_ANIMATION_TYPE)
                #TODO: use reflection to instantiate:
                animation = PanZoomAnimation(npImCurrent, animationSpec)

                # Generate frames
                duration = image['duration']
                nframes = int(duration * framerate)
                for i in range(0, nframes):
                    print("processing %s frame %d" % (image['file'], i))

                    # Animate image
                    #TODO: use transitionDuration of NEXT image
                    t = self.getTForFrame(i, duration + transitionDuration, framerate)
                    npIm1 = animation.animate(t)
                    
                    # Transition
                    transitionAlpha = 1.0 if (transitionDuration == 0) else i / (transitionDuration * framerate)
                    if transitionAlpha < 1.0:
                        # Animate previous image
                        t = self.getTForFrame(prevDuration * framerate + i,
                            prevDuration + transitionDuration, framerate)
                        npIm0 = prevAnimation.animate(t)

                        # Combine transition images
                        npResult = ((1.0 - transitionAlpha) * npIm0 + transitionAlpha * npIm1).astype('uint8')
                    else:
                        npResult = npIm1

                    # Write frame to video
                    writer.append_data(npResult)

                    # Write frame to image if set up
                    if outputFrames != '':
                        imageio.imwrite(outputFrames % globalFrameN, npResult)
                    globalFrameN += 1

                prevAnimation = animation
                prevDuration = duration

            writer.close()
    
    # Scales the frameNumber to the current position in the animation to a fraction
    # between 0 and 1.
    # totalDuration should include the animation duration for the current image and the
    # transition duration to the next image
    def getTForFrame(self, frameNumber, totalDuration, frameRate):
        return frameNumber / (totalDuration * frameRate)
    

if __name__ == "__main__":
    scriptor = Scriptor()
    scriptor.generateVideo()
