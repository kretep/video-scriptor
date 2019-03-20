import os
import numpy as np
import imageio
import yaml
import random
import subprocess
from panzoomanimation import PanZoomAnimation
from blendtransition import BlendTransition
from properties import Spec, Props

class Scriptor:

    def generateVideo(self):
        with open('video.spec.yml') as t:
            self.rootSpec = rootSpec = Spec(yaml.safe_load(t), None)
            self.framerate = rootSpec.get(Props.FRAME_RATE)
            self.outputFrames = rootSpec.get(Props.OUTPUT_FRAMES)
            self.limitFrames = rootSpec.get('limitframes')
            random.seed(rootSpec.get('randomseed'))

            filename = rootSpec.get(Props.OUTPUT_FILE)
            videoOut = os.path.join('output', filename)

            # Initialize writer
            self.writer = imageio.get_writer(videoOut, 
                fps=self.framerate,
                macro_block_size=8)

            self.prevAnimation = None
            self.prevDuration = 0

            # Process images in script
            self.globalFrameN = 0
            images = rootSpec.get(Props.IMAGES)
            self.processImages(images, rootSpec)

            self.writer.close()

            # Join audio
            audioSpec = rootSpec.getSpec('audio')
            if audioSpec != None:
                self.combineVideoWithAudio(audioSpec, videoOut, os.path.join('output', 'combined.mp4'))
    
    def processImages(self, images, parentSpec):
        for item in images: # TODO: make spec.get return arry of Spec instead of array of dicts
            itemSpec = Spec(item, parentSpec)
            subgroup = itemSpec.get('images', None, doRecurse=False)
            if (subgroup != None):
                # Recurse
                self.processImages(subgroup, itemSpec)
            else:
                self.processImage(itemSpec)
            
            # Stop early
            if (self.limitFrames != None and self.globalFrameN >= self.limitFrames):
                break

    def processImage(self, imageSpec):
        # Read image
        inputFileName = imageSpec.get(Props.IMAGE_FILE)
        npImCurrent = imageio.imread('./input/%s' % inputFileName)
        
        # Set up transition
        #TODO: relfect: transitionType = transitionSpec.get('type', 'blend')
        transition = BlendTransition()
        transitionDuration = imageSpec.get('transitiontime', 0.5)

        # Set up animation
        #animationType = animationSpec.get(Props.IMAGE_ANIMATION_TYPE)
        #TODO: use reflection to instantiate:
        animation = PanZoomAnimation(npImCurrent, imageSpec)

        # Generate frames
        duration = imageSpec.get('duration', 2.0)
        nframes = int(duration * self.framerate)
        for i in range(0, nframes):
            print("processing %s frame %d" % (inputFileName, i))

            # Animate image
            #TODO: use transitionDuration of NEXT image
            animationT = self.getTForFrame(i, duration + transitionDuration, self.framerate)
            npIm1 = animation.animate(animationT)
            
            # Transition
            transitionT = 1.0 if (transitionDuration == 0) else i / (transitionDuration * self.framerate)
            if transitionT < 1.0 and self.prevAnimation != None:
                # Animate previous image
                animationT = self.getTForFrame(self.prevDuration * self.framerate + i,
                    self.prevDuration + transitionDuration, self.framerate)
                npIm0 = self.prevAnimation.animate(animationT)

                # Combine transition images
                npResult = transition.processTransition(npIm0, npIm1, transitionT)
            else:
                npResult = npIm1

            # Write frame to video
            self.writer.append_data(npResult)

            # Write frame to image if set up
            if self.outputFrames != '':
                imageio.imwrite(self.outputFrames % self.globalFrameN, npResult)
            
            self.globalFrameN += 1
            if (self.limitFrames != None and self.globalFrameN >= self.limitFrames):
                break

        self.prevAnimation = animation
        self.prevDuration = duration


    # Scales the frameNumber to the current position in the animation to a fraction
    # between 0 and 1.
    # totalDuration should include the animation duration for the current image and the
    # transition duration to the next image
    def getTForFrame(self, frameNumber, totalDuration, frameRate):
        return frameNumber / (totalDuration * frameRate)
    
    def combineVideoWithAudio(self, audioSpec, videoIn, videoOut):
        def maybe(option, key, spec):
            value = spec.get(key)
            return [option, str(value)] if value != None else []
        audioIn = audioSpec.get('file')
        cmd_out = ['ffmpeg',
                '-y',
                '-i', videoIn,
                *maybe('-ss', 'audiooffset', audioSpec),
                *maybe('-itsoffset', 'videooffset', audioSpec),
                '-i', audioIn,
                '-c', 'copy',
                '-map', '0:v',
                '-map', '1:a',
                '-shortest',
                videoOut]
        pipe = subprocess.Popen(cmd_out)
        pipe.wait()

if __name__ == "__main__":
    scriptor = Scriptor()
    scriptor.generateVideo()
