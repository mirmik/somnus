import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

import threading

import cv2
import aiohttp
from aiohttp import web
import aiortc
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay
from av import VideoFrame

import numpy as np
import cv2 as cv
import NDIlib as ndi

class Client:
    def __init__(self, pc):
        self.pc = pc
    
    def video_sender(self):
        senders = self.pc.getSenders()
        vs = senders.find(lambda s: s.track.kind == "video")
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

VIDEO_TRACKS = set()
SERVER_MESSAGE_LISTENERS = set()

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

def on_datachannel_handler(channel):
    print("DATACHANNEL", channel.label)

    if channel.label == "server-message":
        SERVER_MESSAGE_LISTENERS.add(channel)

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


    @pc.on("datachannel")
    def on_datachannel(channel):
        on_datachannel_handler(channel)

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
            obj = pc.addTrack(
                VideoTransformTrack(
                    relay.subscribe(track, buffered=False), transform=params["video_transform"]
                )
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
    
    
    async def async_send_server_message():
        while True:
            await control_message("HelloWorld")
            await asyncio.sleep(1)

    sender_task = async_send_server_message()
    web_server_task = web._run_app(
        app, 
        access_log=None, 
        host=args.host, 
        port=args.port, 
        ssl_context=ssl_context
    )

    await asyncio.gather(
        web_server_task,
        sender_task
    )

if __name__ == "__main__":
    asyncio.run(main())