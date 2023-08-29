import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

import threading

import cv2
import numpy
import math
import aiohttp
from aiohttp import web
import aiortc
from aiortc import MediaStreamTrack, VideoStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay
from av import VideoFrame

import numpy as np
import cv2 as cv
import NDIlib as ndi

VIDEO_TRACKS = set()
SERVER_MESSAGE_LISTENERS = set()
REMOTE_TRACKS = list()

class Client:
    def __init__(self, pc):
        self.pc = pc
    
    def video_sender(self):
        senders = self.pc.getSenders()
        vs = [s for s in senders if s.track.kind == "video"][0]
        return vs


ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
#pcs = set()

clients = set()

def client_of_pc(pc):
    for c in clients:
        if c.pc is pc:
            return c 

relay = MediaRelay()

send_settings = ndi.SendCreate()
send_settings.ndi_name = 'ndi-python'
ndi_send = ndi.send_create(send_settings)
ndi_video_frame = ndi.VideoFrameV2()

class FlagVideoStreamTrack(VideoStreamTrack):
    """
    A video track that returns an animated flag.
    """

    def __init__(self, colors):
        super().__init__()  # don't forget this!
        self.counter = 0
        height, width = 480, 640
        self.label = "LABEL FLAG"

        # generate flag
        data_bgr = numpy.hstack(
            [
                self._create_rectangle(
                    width=213, height=480, color=colors[0]
                ),  # blue
                self._create_rectangle(
                    width=214, height=480, color=colors[1]
                ),  # white
                self._create_rectangle(width=213, height=480, color=colors[2]),  # red
            ]
        )

        # shrink and center it
        M = numpy.float32([[0.5, 0, width / 4], [0, 0.5, height / 4]])
        data_bgr = cv2.warpAffine(data_bgr, M, (width, height))

        # compute animation
        omega = 2 * math.pi / height
        id_x = numpy.tile(numpy.array(range(width), dtype=numpy.float32), (height, 1))
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

    async def recv(self):
        if (not self.inited):
            self.inited = True
            print("VideoTransformTrack inited")

        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        img = cv2.cvtColor(cv2.Canny(img, 100, 200), cv2.COLOR_GRAY2BGR)
        ndi_video_frame.data = img
        ndi_video_frame.FourCC = ndi.FOURCC_VIDEO_TYPE_RGBX
        ndi.send_send_video_v2(ndi_send, ndi_video_frame)
        return frame

async def index(request):
    print("INDEX")
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    print("JAVASCRIPT")
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)

rgb_flag = FlagVideoStreamTrack(
                [(255,0,0), (0,255,0), (0,0,255)]
            )

def on_datachannel_handler(channel, pc):
    print("DATACHANNEL", channel.label)

    if channel.label == "server-message":
        SERVER_MESSAGE_LISTENERS.add(channel)
        @channel.on("message")
        def on_message(message):
            print("REMOTE_COMMAND:", message)
            client = client_of_pc(pc)
            video_sender = client.video_sender()
            video_sender.replaceTrack(REMOTE_TRACKS[0])
    else:
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    asyncio.ensure_future(track_list_updated())


async def control_message(msg):
    print("CONTROL_MESSAGE", msg, len(SERVER_MESSAGE_LISTENERS))
    to_remove = []
    for channel in SERVER_MESSAGE_LISTENERS:
        try:
            channel.send("HelloWorld")
        except aiortc.exceptions.InvalidStateError:
            to_remove.append(channel)
    for ch in to_remove:
        SERVER_MESSAGE_LISTENERS.remove(ch)
            

async def track_list_updated():
    print("TRACK LIST UPDATED")
    await control_message("Control Message")


async def offer(request):
    print("OFFER")
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    clients.add(Client(pc))

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    log_info("Created for %s", request.remote)

    flag_track = FlagVideoStreamTrack(
        [(0,255,255),(255,0,255), (255,255,0)]
    )
    flag_sender = pc.addTrack(flag_track)
    
    @pc.on("datachannel")
    def on_datachannel(channel):
        on_datachannel_handler(channel, pc)
        #pc.addTrack(FlagVideoStreamTrack())
    

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("CONNECTIIONSTAGE", pc.connectionState)
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            client = client_of_pc(pc)
            clients.discard(client)

    recorder = MediaBlackhole()
    @pc.on("track")
    def on_track(track):
        print("TRACK")
        log_info("Track %s received", track.kind)

        if track.kind == "audio":
            pass
        #    pc.addTrack(player.audio)
        elif track.kind == "video":
            print("ADD NEW TRACK")
            #VIDEO_TRACKS.add(track)
            #asyncio.ensure_future(track_list_updated())
            
            TRANSFORM_TRACK = VideoTransformTrack(
                    relay.subscribe(track, buffered=False), transform=params["video_transform"]
                )
            REMOTE_TRACKS.append(TRANSFORM_TRACK)
            obj = pc.addTrack(
                TRANSFORM_TRACK
            )
            print(obj)

            #recorder.addTrack(relay.subscribe(track))

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)

    
    # handle offer
    await pc.setRemoteDescription(offer)


    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    # close peer connections
    print("SHUTDOWN")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def main():
    parser = argparse.ArgumentParser(
        description="WebRTC audio / video / data-channels demo"
    )
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--record-to", help="Write received media to a file."),
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    
    
    #async def async_send_server_message():
    #    while True:
    #        await control_message("HelloWorld")
    #        await asyncio.sleep(1)

    #sender_task = async_send_server_message()
    web_server_task = web._run_app(
        app, 
        access_log=None, 
        host=args.host, 
        port=args.port, 
        ssl_context=ssl_context
    )

    await asyncio.gather(
        web_server_task,
    #    sender_task
    )

if __name__ == "__main__":
    asyncio.run(main())