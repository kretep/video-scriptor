import sys
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
from spec import Spec, ImageSpec

def getFromQueue(queue):
    result = None
    try:
        result = queue.get_nowait()
    except:
        pass
    return result

class Scriptor:
    """
    The phases of processing:
    - Set up data structures and global attributes
    - Prepare image specs and organize them
    - Launch one thread to initialize image spec (read input image, set up (random) attributes for animation and transition)
    - Launch multiple threads to generate frames and store results
    - In main thread: wait for results and write to video
    - Join video with audio
    """
    def generateVideo(self, scriptFile):
        with open(scriptFile) as t:
            self.rootSpec = Spec(yaml.safe_load(t), None)

        rootSpec = self.rootSpec
        self.framerate = rootSpec.get('framerate', 30)
        self.frameWidth = rootSpec.get('framewidth', 1440)
        self.frameHeight = rootSpec.get('frameheight', 1080)
        self.outputFrames = rootSpec.get('outputframes')
        self.limitFrames = rootSpec.get('limitframes')
        random.seed(rootSpec.get('randomseed'))

        outputFile = rootSpec.get('outputfile', 'video.mp4')
        videoOut = outputFile + '.temp.mp4'

        # Initialize data structures
        self.imageSpecQueue = queue.Queue()
        self.imageFrameQueue = queue.Queue()
        self.resultQueue = queue.Queue()
        self.prevSpec = None
        self.allImageSpecsInitialized = False

        # Prepare data structures for processing
        images = rootSpec.get('images', [])
        self.prepareImageSpecs(images, rootSpec)

        # Start one thread to initialize image specs
        threading.Thread(target=self.runnableInitImageSpecs).start()
        
        # Start processing image specs by launching worker threads
        self.globalFrameN = 0
        for _ in range(self.rootSpec.get('threads', 16)):
            threading.Thread(target=self.runnableProcessFrame).start()

        # In the current thread, wait for and write the results
        self.writer = imageio.get_writer(videoOut, 
            fps=self.framerate,
            macro_block_size=8)
        self.processResults()
        self.writer.close()

        # Join audio
        audioSpec = rootSpec.getSpec('audio')
        if not audioSpec is None:
            self.combineVideoWithAudio(audioSpec, videoOut, outputFile)
    
    def prepareImageSpecs(self, images, parentSpec):
        """ Walks through the image specs recursively, in order, links them, adds them to the queues.
        """
        for item in images:
            itemSpec = ImageSpec(item, parentSpec)

            subgroup = itemSpec.get('images', None, doRecurse=False)
            if subgroup is None:
                # Set required variable in prev spec from current spec
                if not self.prevSpec is None:
                    self.prevSpec.nextTransitionDuration = itemSpec.get('transitiontime', 0)

                # Link and remember previous
                itemSpec.prevSpec = self.prevSpec
                self.prevSpec = itemSpec

                # Put in queues
                self.imageSpecQueue.put(itemSpec)
                self.resultQueue.put(itemSpec)
            else:
                # Recurse
                self.prepareImageSpecs(subgroup, itemSpec)
    
    def runnableInitImageSpecs(self):
        # Initialize image specs while they are available
        # (the queue is pre-filled, so when it's empty, we're done)
        imageSpec = getFromQueue(self.imageSpecQueue)
        while not imageSpec is None:
            self.initializeImageSpec(imageSpec)

            # Wait with initializing next image spec.
            # (we don't want to initialize and load too early, to limit memory usage,
            # but we also don't want to load too late, because it will block the threads,
            # so start loading when we have less than a certain amount of frames to process)
            while self.imageFrameQueue.qsize() > 60:
                time.sleep(0.1)

            imageSpec = getFromQueue(self.imageSpecQueue)
        
        # Flag that allows frame processing threads to finish if there are no more frames
        self.allImageSpecsInitialized = True
        print("finished processing image specs")

    def initializeImageSpec(self, imageSpec):
        # Read image
        inputFileName = imageSpec.get('file')
        #assert not inputFileName is None, 'No input file specified'
        if inputFileName is None:
            npImCurrent = np.zeros((self.frameHeight, self.frameWidth, 3), dtype='uint8')
        else:
            npImCurrent = imageio.imread('./input/%s' % inputFileName)
        
        # Set up transition
        #TODO: relfect: transitionType = transitionSpec.get('type', 'blend')
        imageSpec.transition = BlendTransition()

        # Set up animation
        #animationType = animationSpec.get(Props.IMAGE_ANIMATION_TYPE)
        #TODO: use reflection to instantiate:
        imageSpec.animation = PanZoomAnimation(npImCurrent, imageSpec)
        imageSpec.duration = duration = imageSpec.get('duration', 2.0)
        

        nframes = int(duration * self.framerate)
        imageSpec.frames = [None] * nframes
        for i in range(0, nframes):
            self.imageFrameQueue.put((imageSpec, i))

    def runnableProcessFrame(self):
        imageFrame = getFromQueue(self.imageFrameQueue)
        while (not imageFrame is None) or (not self.allImageSpecsInitialized):

            # Either we have an image to process or we have to wait for one
            if not imageFrame is None:
                (imageSpec, frameNr) = imageFrame
                self.processFrame(imageSpec, frameNr)
            else:
                time.sleep(0.1)

            imageFrame = getFromQueue(self.imageFrameQueue)

        print("finished processing frames")
        
    def processFrame(self, imageSpec, i):
        prevSpec = imageSpec.prevSpec
        transitionDuration = imageSpec.get('transitiontime', 0.5)
        duration = imageSpec.duration
        nextTransitionDuration = imageSpec.nextTransitionDuration
        animation = imageSpec.animation
        transition = imageSpec.transition

        print("processing %s frame %d/%d" % (imageSpec.get('file'), i + 1, len(imageSpec.frames)))

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

        # Put result in list to be written
        imageSpec.frames[i] = npResult

    def processResults(self):
        # self.resultQueue has been prefilled (to keep results in the correct order),
        # so we just need to keep going until it is empty
        currentResult = getFromQueue(self.resultQueue)
        while not currentResult is None:

            # Wait for initialization
            while currentResult.frames is None:
                time.sleep(0.1)

            # Wait for and process each result frame in order
            for i in range(len(currentResult.frames)):
                # Wait for result
                while currentResult.frames[i] is None:
                    time.sleep(0.1)
                # Process result
                self.writeResultImage(currentResult.frames[i])
                # Clean up
                currentResult.frames[i] = None

            # Clean up unused references to free memory
            if not currentResult.prevSpec is None:
                # Clean up finished spec so memory can be released
                currentResult.prevSpec.animation = None
                currentResult.prevSpec.transition = None
                currentResult.prevSpec = None

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
                #'-c', 'copy',
                '-map', '0:v',
                '-map', '1:a',
                '-shortest',
                '-filter:a', 'afade=t=out:st=144:d=8',
                videoOut]
        pipe = subprocess.Popen(cmd_out)
        pipe.wait()

if __name__ == "__main__":
    scriptor = Scriptor()
    scriptor.generateVideo(sys.argv[1])
