import os
import numpy as np
import imageio
import yaml
from panzoomanimation import PanZoomAnimation
from properties import Spec, Props

class Scriptor:

    def generateVideo(self):
        with open('video.spec.yml') as t:
            self.rootSpec = rootSpec = Spec(yaml.safe_load(t), None)
            self.framerate = rootSpec.get(Props.FRAME_RATE)
            self.outputFrames = rootSpec.get(Props.OUTPUT_FRAMES)

            # Initialize writer
            filename = rootSpec.get(Props.OUTPUT_FILE)
            self.writer = imageio.get_writer(os.path.join('output', filename), fps=self.framerate)

            self.prevAnimation = None
            self.prevDuration = 0

            # Process images in script
            self.globalFrameN = 0
            images = rootSpec.get(Props.IMAGES)
            self.processImages(images, rootSpec)

            self.writer.close()
    
    def processImages(self, images, parentSpec):
        for item in images: # TODO: make spec.get return arry of Spec instead of array of dicts
            itemSpec = Spec(item, parentSpec)
            subgroup = itemSpec.get('images', None, doRecurse=False)
            if (subgroup != None):
                # Recurse
                self.processImages(subgroup, itemSpec)
            else:
                self.processImage(itemSpec)

    def processImage(self, imageSpec):
        # Read image
        inputFileName = imageSpec.get(Props.IMAGE_FILE)
        npImCurrent = imageio.imread('./input/%s' % inputFileName)
        
        # Some administration for transition
        transitionDict = imageSpec.get('transition', { 'type': 'blend', 'duration': 0.5 })
        transition = Spec(transitionDict, imageSpec)
        transitionDuration = transition.get('duration', 0.5)
        transitionType = transition.get('type', 'blend')

        # Same for animation
        animationSpecDict = imageSpec.get(Props.IMAGE_ANIMATION)
        animationSpec = Spec(animationSpecDict, imageSpec)
        animationType = animationSpec.get(Props.IMAGE_ANIMATION_TYPE)
        #TODO: use reflection to instantiate:
        animation = PanZoomAnimation(npImCurrent, animationSpec)

        # Generate frames
        duration = imageSpec.get('duration', 2.0)
        nframes = int(duration * self.framerate)
        for i in range(0, nframes):
            print("processing %s frame %d" % (inputFileName, i))

            # Animate image
            #TODO: use transitionDuration of NEXT image
            t = self.getTForFrame(i, duration + transitionDuration, self.framerate)
            npIm1 = animation.animate(t)
            
            # Transition
            transitionAlpha = 1.0 if (transitionDuration == 0) else i / (transitionDuration * self.framerate)
            if transitionAlpha < 1.0 and self.prevAnimation != None:
                # Animate previous image
                t = self.getTForFrame(self.prevDuration * self.framerate + i,
                    self.prevDuration + transitionDuration, self.framerate)
                npIm0 = self.prevAnimation.animate(t)

                # Combine transition images
                npResult = ((1.0 - transitionAlpha) * npIm0 + transitionAlpha * npIm1).astype('uint8')
            else:
                npResult = npIm1

            # Write frame to video
            self.writer.append_data(npResult)

            # Write frame to image if set up
            if self.outputFrames != '':
                imageio.imwrite(self.outputFrames % self.globalFrameN, npResult)
            self.globalFrameN += 1

        self.prevAnimation = animation
        self.prevDuration = duration


    # Scales the frameNumber to the current position in the animation to a fraction
    # between 0 and 1.
    # totalDuration should include the animation duration for the current image and the
    # transition duration to the next image
    def getTForFrame(self, frameNumber, totalDuration, frameRate):
        return frameNumber / (totalDuration * frameRate)
    

if __name__ == "__main__":
    scriptor = Scriptor()
    scriptor.generateVideo()
