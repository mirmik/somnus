from aiortc import MediaStreamTrack
from av import AudioFrame, VideoFrame
import numpy as np


class AudioTransformTrack(MediaStreamTrack):
    """
    A audio stream track that transforms frames from an another track.
    """

    kind = "audio"

    def __init__(self, track):
        super().__init__()  # don't forget this!
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        return frame


class SilenceAudioStreamTrack(MediaStreamTrack):
    """
    A video stream track that returns a silent frame.
    """

    kind = "audio"

    def __init__(self):
        super().__init__()  # don't forget this!

    async def recv(self):
        audio = np.zeros((1, 2048), dtype=np.int16)
        frame = AudioFrame.from_ndarray(audio, layout='mono', format='s16')
        frame.sample_rate = 16000  # remember to set rate !
        #frame.timestamp = 0
        return frame
