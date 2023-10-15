from aiortc import MediaStreamTrack, VideoStreamTrack
import numpy
import cv2 as cv
import cv2
import math
from av import VideoFrame
import json
import numpy as np
import cv2 as cv
import NDIlib as ndi


class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track, transform):
        super().__init__()  # don't forget this!
        self.track = track
        self.transform = transform
        self.inited = False
        self.ndi_enabled = False

        #self.send_settings = ndi.SendCreate()
        #self.send_settings.ndi_name = 'ndi-python'
        #self.ndi_send = ndi.send_create(self.send_settings)
        #self.ndi_video_frame = ndi.VideoFrameV2()

    def enable_ndi(self, en):
        self.ndi_enabled = en

    async def recv(self):
        if (not self.inited):
            self.inited = True
            print("VideoTransformTrack inited")

        frame = await self.track.recv()
        if (self.ndi_enabled):
            img = frame.to_ndarray(format="bgr24")
            #img = cv2.cvtColor(cv2.Canny(img, 100, 200), cv2.COLOR_GRAY2BGR)
            #self.ndi_video_frame.data = img
            #self.ndi_video_frame.FourCC = ndi.FOURCC_VIDEO_TYPE_BGRX
            #ndi.send_send_video_v2(self.ndi_send, self.ndi_video_frame)
        return frame


class FlagVideoStreamTrack(VideoStreamTrack):
    """
    A video track that returns an animated flag.
    """

    def __init__(self, colors):
        super().__init__()  # don't forget this!
        self.counter = 0
        height, width = 240, 320
        self.label = "LABEL FLAG"

        # generate flag
        data_bgr = numpy.hstack(
            [
                self._create_rectangle(
                    width=213//2, height=480//2, color=colors[0]
                ),  # blue
                self._create_rectangle(
                    width=214//2, height=480//2, color=colors[1]
                ),  # white
                self._create_rectangle(
                    width=213//2, height=480//2, color=colors[2])
            ]
        )

        # shrink and center it
        M = numpy.float32([[0.5, 0, width / 4], [0, 0.5, height / 4]])
        data_bgr = cv2.warpAffine(data_bgr, M, (width, height))

        # compute animation
        omega = 2 * math.pi / height
        id_x = numpy.tile(numpy.array(
            range(width), dtype=numpy.float32), (height, 1))
        id_y = numpy.tile(
            numpy.array(range(height), dtype=numpy.float32), (width, 1)
        ).transpose()

        self.frames = []
        for k in range(30):
            phase = 2 * k * math.pi / 30
            map_x = id_x + 10 * numpy.cos(omega * id_x + phase)
            map_y = id_y + 10 * numpy.sin(omega * id_x + phase)
            self.frames.append(
                VideoFrame.from_ndarray(
                    cv2.remap(data_bgr, map_x, map_y, cv2.INTER_LINEAR), format="bgr24"
                )
            )

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame = self.frames[self.counter % 30]
        frame.pts = pts
        frame.time_base = time_base
        self.counter += 1
        return frame

    def _create_rectangle(self, width, height, color):
        data_bgr = numpy.zeros((height, width, 3), numpy.uint8)
        data_bgr[:, :] = color
        return data_bgr
