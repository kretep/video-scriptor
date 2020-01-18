
# Video Scriptor

Video Scriptor generates a slideshow video from images based on a script configuration (yaml) file. Currently it supports pan-zoom animations (random or fully specified) and blending image transitions.

The program can be run with:

```
python scriptor.py script.yml
```

## Script configuration

Here's a simple script:

```
outputfile: video.mp4
framerate: 30
framewidth: 1440
frameheight: 1080

images:
  - 
    duration: 3.5
    animation: panzoom
    transition: blend
    transitiontime: 1.0
    images:
      - file: DSC02601.JPG
        duration: 5.0 # override duration
      - file: DSC02639.JPG
      - file: DSC02625.JPG
      - file: DSC02485.JPG
      - generate: black
```

The configuration allows images to be hierarchically grouped in a kind of scopes, to prevent having to specify attributes for each image separately. Every attribute is looked up recursively in this scope. For instance, if the duration is not specified for an image, it is looked up in the parent scope. (In the above script, it will be 3.5 seconds for each image except the first one).

Have a look at one of the [sample configuration files](samples/) for an explanation of all the attributes and a demonstration of more complex use cases.

## Some notes on the code

### Required Python packages

- imageio
- imageio-ffmpeg
- numpy
- pyyaml
- scikit-image
- scipy

### Parallel processing

The script uses multiple threads for parallel processing. However, a number of tasks must be processed in order, such as writing the resulting frames to the video :) But also generation of random values is done in order, to make the generated video reproducible (using a random seed). One thread is used for initalization of random values, multiple threads generate the frames in parallel and the results are written in the main thread.

### Streaming

All of this is done in a streaming fashion, i.e. images are not loaded before they are required and they are unloaded when they are not needed anymore. Frames are written to file using ffmpeg's piping functionality. This keeps memory usage as low as possible.
