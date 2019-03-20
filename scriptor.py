import os
import numpy as np
import imageio
import yaml
import random
import subprocess
from panzoomanimation import PanZoomAnimation
from blendtransition import BlendTransition
from spec import Spec

class Scriptor:

    def generateVideo(self):
        with open('video.spec.yml') as t:
            self.rootSpec = rootSpec = Spec(yaml.safe_load(t), None)
            self.framerate = rootSpec.get('framerate', 30)
            self.outputFrames = rootSpec.get('outputframes')
            self.limitFrames = rootSpec.get('limitframes')
            random.seed(rootSpec.get('randomseed'))

            filename = rootSpec.get('outputfile', 'video.mp4')
            videoOut = os.path.join('output', filename)

            # Initialize writer
            self.writer = imageio.get_writer(videoOut, 
                fps=self.framerate,
                macro_block_size=8)

            # Parse images in script
            self.allImageSpecs = [] # flat list of image specs
            self.prevSpec = None
            images = rootSpec.get('images', [])
            self.parseImages(images, rootSpec)

            # Process images
            self.globalFrameN = 0
            self.processImages(self.allImageSpecs)

            self.writer.close()

            # Join audio
            audioSpec = rootSpec.getSpec('audio')
            if audioSpec != None:
                self.combineVideoWithAudio(audioSpec, videoOut, os.path.join('output', 'combined.mp4'))
    
    def parseImages(self, images, parentSpec):
        for item in images:
            itemSpec = Spec(item, parentSpec)

            subgroup = itemSpec.get('images', None, doRecurse=False)
            if (subgroup != None):
                # Recurse
                self.parseImages(subgroup, itemSpec)
            else:
                # Put in flat list
                if self.prevSpec != None:
                    self.prevSpec.nextSpec = itemSpec
                itemSpec.prevSpec = self.prevSpec
                self.prevSpec = itemSpec
                self.allImageSpecs.append(itemSpec)
            
    def processImages(self, imageSpecs):
        for imageSpec in imageSpecs:
            self.processImage(imageSpec)

    def processImage(self, imageSpec):
        prevSpec = imageSpec.prevSpec
        nextSpec = imageSpec.nextSpec

        # Read image
        inputFileName = imageSpec.get('file')
        assert inputFileName != None, 'No input file specified'
        npImCurrent = imageio.imread('./input/%s' % inputFileName)
        
        # Set up transition
        #TODO: relfect: transitionType = transitionSpec.get('type', 'blend')
        imageSpec.transition = transition = BlendTransition()
        transitionDuration = imageSpec.get('transitiontime', 0.5)
        nextTransitionDuration = nextSpec.get('transitiontime', 0.5)

        # Set up animation
        #animationType = animationSpec.get(Props.IMAGE_ANIMATION_TYPE)
        #TODO: use reflection to instantiate:
        imageSpec.animation = animation = PanZoomAnimation(npImCurrent, imageSpec)
        imageSpec.duration = duration = imageSpec.get('duration', 2.0)
        
        #TODO: Notify of init complete

        # Generate frames
        nframes = int(duration * self.framerate)
        for i in range(0, nframes):
            print("processing %s frame %d" % (inputFileName, i))

            # Animate image
            animationT = self.getTForFrame(i, duration + nextTransitionDuration, self.framerate)
            npIm1 = animation.animate(animationT)
            
            # Transition
            transitionT = 1.0 if (transitionDuration == 0) else i / (transitionDuration * self.framerate)
            if transitionT < 1.0 and prevSpec != None:
                # Animate previous image
                animationT = self.getTForFrame(prevSpec.duration * self.framerate + i,
                    prevSpec.duration + transitionDuration, self.framerate)
                npIm0 = prevSpec.animation.animate(animationT)

                # Combine transition images
                npResult = transition.processTransition(npIm0, npIm1, transitionT)
            else:
                npResult = npIm1

            # Write frame to video
            self.writer.append_data(npResult)

            # Write frame to image if set up
            if self.outputFrames != None:
                imageio.imwrite(self.outputFrames % self.globalFrameN, npResult)
            
            self.globalFrameN += 1
            if (self.limitFrames != None and self.globalFrameN >= self.limitFrames):
                break


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
