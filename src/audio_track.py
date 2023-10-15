from aiortc import MediaStreamTrack
from aiortc.mediastreams import AudioStreamTrack
from av import AudioFrame, VideoFrame
import numpy as np
import asyncio


class AudioTransformTrack(AudioStreamTrack):
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


class SilenceAudioStreamTrack(AudioStreamTrack):
    """
    A video stream track that returns a silent frame.
    """

    kind = "audio"

    def __init__(self):
        super().__init__()  # don't forget this!

    async def recv(self):
        audio = np.zeros((1, 2048), dtype='int16')
        frame = AudioFrame.from_ndarray(audio, layout='mono', format='s16')
        frame.sample_rate = 48000  # remember to set rate !
        # set timestamp
        frame.pts = 0
        return frame


class AccumulateAudioTrack(AudioStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()
        self.tracks = []

    def add_track(self, track):
        self.tracks.append(track)

    async def recv(self):
        audio = np.zeros((1, 2048), dtype='int16')
        frame = AudioFrame.from_ndarray(audio, layout='mono', format='s16')
        frame.sample_rate = 48000  
        frame.pts = 0
        return frame


    
    