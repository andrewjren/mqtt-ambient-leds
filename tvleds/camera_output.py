import numpy as np
from threading import Lock

# CameraOutput manages the output buffer of the camera
class CameraOutput(object):
    def __init__(self, frame_width, frame_height):
        self.frame = np.zeros((frame_width,frame_height,3))
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.lock = Lock()

    def write(self, buf):
        image = np.frombuffer(buf,dtype=np.uint8)

        self.lock.acquire()
        self.frame = image.reshape((self.frame_width,self.frame_height,3))
        self.lock.release()