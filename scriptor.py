import os
import numpy as np
import imageio
import yaml
from panzoomanimation import PanZoomAnimation

class Scriptor:

    def generateVideo(self):
        with open('video.spec.yml') as t:
            script = yaml.safe_load(t)
            framerate = script['framerate']
            outputFrames = script['outputframes'] if 'outputframes' in script else ""

            # Initialize writer
            writer = imageio.get_writer(os.path.join('output', script['outputfile']), fps=framerate)

            npImPrev = None #todo: make empty/black image
            prevAnimation = None
            prevDuration = 0

            # Process images in script
            images = script['images']
            globalFrameN = 0
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
                    if outputFrames:
                        imageio.imwrite(outputFrames % globalFrameN, npResult)
                    globalFrameN += 1

                npImPrev = npImCurrent
                prevAnimation = animation
                prevDuration = duration

            writer.close()
    
    # totalDuration should include the animation duration for the current image and the
    # transition duration to the next image
    def getTForFrame(self, frameNumber, totalDuration, frameRate):
        return frameNumber / (totalDuration * frameRate)
    

if __name__ == "__main__":
    scriptor = Scriptor()
    scriptor.generateVideo()
