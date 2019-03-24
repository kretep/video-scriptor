import os
import numpy as np
import imageio
import yaml
import random
import subprocess
import queue
import threading
import time
from panzoomanimation import PanZoomAnimation
from blendtransition import BlendTransition
from spec import Spec

class ResultHolder:
    def __init__(self):
        self.hasInitialized = False
        self.isFinished = False
        self.imageQueue = queue.Queue()


def getFromQueue(queue):
    result = None
    try:
        result = queue.get_nowait()
    except:
        pass
    return result

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

            # Initialize data structures
            self.imageSpecQueue = queue.Queue()
            self.resultQueue = queue.Queue()
            self.prevSpec = None
            images = rootSpec.get('images', [])

            # Parse images in script
            self.parseImages(images, rootSpec)

            # Start processing image specs by launching worker threads
            self.globalFrameN = 0
            for _ in range(self.rootSpec.get('threads', 16)):
                threading.Thread(target=self.threadRunnable).start()

            # In the current thread, wait for and write the results
            self.writer = imageio.get_writer(videoOut, 
                fps=self.framerate,
                macro_block_size=8)
            self.processResults()
            self.writer.close()

            # Join audio
            audioSpec = rootSpec.getSpec('audio')
            if not audioSpec is None:
                self.combineVideoWithAudio(audioSpec, videoOut, os.path.join('output', 'combined.mp4'))
    
    def parseImages(self, images, parentSpec):
        """ Walks through the image specs recursively, in order, links them, adds them to a
            queue and creates the holder for the result.
        """
        for item in images:
            itemSpec = Spec(item, parentSpec)

            subgroup = itemSpec.get('images', None, doRecurse=False)
            if (not subgroup is None):
                # Recurse
                self.parseImages(subgroup, itemSpec)
            else:
                # Set up result holder
                itemSpec.resultHolder = ResultHolder()
                self.resultQueue.put(itemSpec.resultHolder)

                # Doubly link
                if not self.prevSpec is None:
                    self.prevSpec.nextSpec = itemSpec
                itemSpec.prevSpec = self.prevSpec

                # Put in queue
                self.imageSpecQueue.put(itemSpec)

                # Remember previous
                self.prevSpec = itemSpec
                
    def threadRunnable(self):
        # Check if there are more image specs to process
        imageSpec = getFromQueue(self.imageSpecQueue)
        while not imageSpec is None:
            self.processImageSpec(imageSpec)
            imageSpec = getFromQueue(self.imageSpecQueue)
        print("finished")

    def processImageSpec(self, imageSpec):
        prevSpec = imageSpec.prevSpec
        nextSpec = imageSpec.nextSpec

        # Read image
        inputFileName = imageSpec.get('file')
        assert not inputFileName is None, 'No input file specified'
        npImCurrent = imageio.imread('./input/%s' % inputFileName)
        
        # Set up transition
        #TODO: relfect: transitionType = transitionSpec.get('type', 'blend')
        imageSpec.transition = transition = BlendTransition()
        transitionDuration = imageSpec.get('transitiontime', 0.5)
        nextTransitionDuration = nextSpec.get('transitiontime', 0.5) if not nextSpec is None else 0

        # Set up animation
        #animationType = animationSpec.get(Props.IMAGE_ANIMATION_TYPE)
        #TODO: use reflection to instantiate:
        imageSpec.animation = animation = PanZoomAnimation(npImCurrent, imageSpec)
        imageSpec.duration = duration = imageSpec.get('duration', 2.0)
        
        # Notify of init complete and wait for previous image init complete
        imageSpec.resultHolder.hasInitialized = True
        if not prevSpec is None:
            while not prevSpec.resultHolder.hasInitialized:
                time.sleep(1)

        # Generate frames
        nframes = int(duration * self.framerate)
        for i in range(0, nframes):
            print("processing %s frame %d" % (inputFileName, i))

            # Animate image
            animationT = self.getTForFrame(i, duration + nextTransitionDuration, self.framerate)
            npIm1 = animation.animate(animationT)
            
            # Transition
            transitionT = 1.0 if (transitionDuration == 0) else i / (transitionDuration * self.framerate)
            if transitionT < 1.0 and not prevSpec is None:
                # Animate previous image
                animationT = self.getTForFrame(prevSpec.duration * self.framerate + i,
                    prevSpec.duration + transitionDuration, self.framerate)
                npIm0 = prevSpec.animation.animate(animationT)

                # Combine transition images
                npResult = transition.processTransition(npIm0, npIm1, transitionT)
            else:
                npResult = npIm1

            # Put result in queue to be written
            imageSpec.resultHolder.imageQueue.put(npResult)
            
        # Flag as finished
        imageSpec.resultHolder.isFinished = True

    def processResults(self):
        # self.resultQueue has been prefilled (to keep results in the correct order),
        # so we just need to keep going until it is empty
        currentResult = getFromQueue(self.resultQueue)
        while not currentResult is None:

            resultImage = getFromQueue(currentResult.imageQueue)
            # Continue until flagged as finished and all images are out of the queue
            while (not currentResult.isFinished) or (not resultImage is None):
                
                # Either we have an image to write or we have to wait for one
                if not resultImage is None:
                    self.writeResultImage(resultImage)
                else:
                    time.sleep(0.2)

                resultImage = getFromQueue(currentResult.imageQueue)

            currentResult = getFromQueue(self.resultQueue)

    def writeResultImage(self, image):
        # Write frame to video
        self.writer.append_data(image)

        # Write frame to image if set up
        if not self.outputFrames is None:
            imageio.imwrite(self.outputFrames % self.globalFrameN, image)
        self.globalFrameN += 1

    # Scales the frameNumber to the current position in the animation to a fraction
    # between 0 and 1.
    # totalDuration should include the animation duration for the current image and the
    # transition duration to the next image
    def getTForFrame(self, frameNumber, totalDuration, frameRate):
        return frameNumber / (totalDuration * frameRate)
    
    def combineVideoWithAudio(self, audioSpec, videoIn, videoOut):
        def maybe(option, key, spec):
            value = spec.get(key)
            return [option, str(value)] if not value is None else []
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
