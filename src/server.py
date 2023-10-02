import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import traceback
import codecs
import sys
import threading
import cv2
import numpy
import signal
import math
import aiohttp
from aiohttp import web
import aiortc
from av import AudioFrame, VideoFrame
from aiortc import MediaStreamTrack, VideoStreamTrack, RTCIceServer, RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay


from client_collection import ClientCollection
from audio_track import AudioTransformTrack, SilenceAudioStreamTrack
from video_track import VideoTransformTrack, FlagVideoStreamTrack
from client import Client

VIDEO_TRACKS = set()
SERVER_MESSAGE_LISTENERS = set()
REMOTE_TRACKS = list()

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
#pcs = set() 

relay = MediaRelay()
audio_relay = MediaRelay()


async def index(request):
    f = codecs.open(os.path.join(ROOT, "assets/index.html"), "r", "utf-8")
    content = f.read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    f = codecs.open(os.path.join(ROOT, "assets/client.js"), "r", "utf-8")
    content = f.read()
    return web.Response(content_type="application/javascript", text=content)

async def stylefile(request):
    f = codecs.open(os.path.join(ROOT, "assets/main.css"), "r", "utf-8")
    content = f.read()
    return web.Response(content_type="text/css", text=content)

rgb_flag = FlagVideoStreamTrack(
                [(255,0,0), (0,255,0), (0,0,255)]
            )

def on_datachannel_handler(channel, pc, client):
    print("DATACHANNEL", channel.label)

    if channel.label == "server-message":
        SERVER_MESSAGE_LISTENERS.add(channel)
        client.set_datachannel(channel)
        ClientCollection.anounce()
        client.send_unique_id()
        ClientCollection.send_system_chat_message("Новый клиент")

        @channel.on("message")        
        def on_message(message):
            client.on_command_message(message)
        
    else:
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])



async def offer(request):
    print("OFFER")
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    #iceServers = []
    #iceServers.append(RTCIceServer('stun:stun.l.google.com:19302'))
    #iceServers.append(RTCIceServer('stun:numb.viagenie.ca'))
    #iceServers.append(RTCIceServer('turn:numb.viagenie.ca', username='username', credential='credential'))
    #pc = RTCPeerConnection(RTCConfiguration(iceServers))
    
    pc = RTCPeerConnection()
    #pc.addIceCandidate(descr)
    
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    client = Client(pc)
    ClientCollection.add_client(client)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    flag_track = FlagVideoStreamTrack(
        [(255,0,0),(0,255,0), (0,0,255)]
    )
    flag_sender = pc.addTrack(flag_track)
    
    @pc.on("datachannel")
    def on_datachannel(channel):
        on_datachannel_handler(channel, pc, client)
        #pc.addTrack(FlagVideoStreamTrack())
    

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("CONNECTIIONSTAGE", pc.connectionState)
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            client = ClientCollection.client_for_pc(pc)
            ClientCollection.discard(client)

    recorder = MediaBlackhole()
    @pc.on("track")
    def on_track(track):
        print("TRACK")
        log_info("Track %s received", track.kind)

        if track.kind == "audio":
            print("ADDED AUDIO TRACK")     
            subscription_track = audio_relay.subscribe(track)
            newtrack = AudioTransformTrack(subscription_track) 
            client.set_audio_track(newtrack)

            #newtrack = SilenceAudioStreamTrack()
            pc.addTrack(newtrack)
        elif track.kind == "video":     
            print("ADDED VIDEO TRACK")      
            newtrack = VideoTransformTrack(
                    relay.subscribe(track, buffered=False), transform=params["video_transform"]
                )
            client.set_video_track(newtrack)
            #obj = pc.addTrack(
            #    newtrack
            #)
            #print(obj)

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
    coros = [cl.pc.close() for cl in ClientCollection.clients]
    await asyncio.gather(*coros)
    ClientCollection.clear()

async def main(cert_file, key_file):
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

    #if args.cert_file:
    if args.cert_file:
        cert_file = args.cert_file
        
    if args.key_file:
        key_file = args.key_file
    
    ssl_context = ssl.SSLContext()
    ssl_context.load_cert_chain(cert_file, key_file)
    #else:
    #    ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_get("/main.css", stylefile)
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

def set_interrupt_handler(handler):
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

if __name__ == "__main__":
    set_interrupt_handler(lambda a,b: sys.exit(0))
    asyncio.run(main(cert_file="assets/cert.pem",key_file="assets/key.pem"))