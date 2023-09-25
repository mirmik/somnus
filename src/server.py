import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import traceback
import codecs
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
import json

import numpy as np
import cv2 as cv
import NDIlib as ndi

VIDEO_TRACKS = set()
SERVER_MESSAGE_LISTENERS = set()
REMOTE_TRACKS = list()

IDCOUNTER = 0

def generate_uniqueid():
    global IDCOUNTER
    IDCOUNTER += 1
    return IDCOUNTER

class ClientsCollection:
    clients = {}

    def __init__(self):
        pass

    @classmethod
    def add_client(cls, client):
        cls.clients[client.unique_id()] = client

    @classmethod
    def identifier_list(cls):
        idslist = list(cls.clients.keys())
        return idslist
    
    @classmethod
    def client_for_pc(cls, pc):
        for cl in cls.clients.values():
            if cl.pc is pc:
                return cl
        return None

    @classmethod
    def clear(cls):
        cls.clients.clear()

    @classmethod
    def send_chat_message(cls, fromid, message):
        for cl in cls.clients.values():
            cl.send_chat_message(fromid, message)

    @classmethod
    def send_system_chat_message(cls, message):
        for cl in cls.clients.values():
            cl.send_chat_message("__SYSTEM__", message)

    #@classmethod
    #def anounce_video_tracks(cls):
    #    for cl in cls.clients.values():
    #        cl.anounce_existance_video()
    
    @classmethod
    def anounce(cls):
        todel = []
        for idx in cls.clients:
            try:
                cls.clients[idx].anounce()
            except: 
                print("Exception in the client:", traceback.format_exc())
                todel.append(idx)

        for idx in todel:    
            del cls.clients[idx]
        
    @classmethod
    def discard(cls, client):
        if client.unique_id() in cls.clients:
            del cls.clients[client.unique_id()]

    @classmethod
    def client_for_id(cls, iden):
        return cls.clients[int(iden)]

class Client:
    def __init__(self, pc):
        self.pc = pc
        self.uniqid = generate_uniqueid()
        self._video_track = None

    def send_chat_message(self, fromid, message):
        msgdct = {
            "cmd" : "chat_message",
            "identifier" : fromid,
            "data" : message 
        }
        self.send_command(json.dumps(msgdct)) 

    def send_unique_id(self):
        msgdct = {
            "cmd" : "set_unique_id",
            "identifier" : self.unique_id() 
        }
        self.send_command(json.dumps(msgdct)) 

    def enable_ndi(self, en):
        self._video_track.enable_ndi(en)

    def set_video_track(self, track):
        self._video_track = track

    def set_audio_track(self, track):
        self._audio_track = track

    def video_sender(self):
        senders = self.pc.getSenders()
        vs = [s for s in senders if s.track and s.track.kind == "video"][0]
        return vs

    def audio_sender(self):
        senders = self.pc.getSenders()
        vs = [s for s in senders if s.track and s.track.kind == "audio"][0]
        return vs

    def video_track(self):
        return self._video_track

    def audio_track(self):
        return self._audio_track

    def unique_id(self):
        return self.uniqid

    def set_datachannel(self, dc):
        self.datachannel = dc

    def send_command(self, msg):
        self.datachannel.send(msg)

    def set_videotrack_for_identifier(self, iden):
        try:
            video_cl = ClientsCollection.client_for_id(iden)
            track = video_cl.video_track()
            self.video_sender().replaceTrack(video_cl.video_track())
        except KeyError as err:
            print("Key is not found:", iden)
            ClientsCollection.anounce()
        except:
            print(traceback.format_exc())

    def set_audiotrack_for_identifier(self, iden):
        try:
            cl = ClientsCollection.client_for_id(iden)
            track = cl.audio_track()
            self.audio_sender().replaceTrack(cl.video_track())
        except KeyError as err:
            print("Key is not found:", iden)
            ClientsCollection.anounce()
        except:
            print(traceback.format_exc())

    def on_command_message(self, msg):
        print("ExternalCommand:", msg)
        dct = json.loads(msg)
        cmd  = dct["cmd"]
        if cmd == "set_video":
            self.set_videotrack_for_identifier(dct["identifier"])
            #self.set_audiotrack_for_identifier(dct["identifier"])
        
        if cmd == "chat_message":
            ClientsCollection.send_chat_message(self.unique_id(), dct["data"])

        if cmd == "ndi_enable":
            self.enable_ndi(dct["state"] == "ON")

    def anounce(self):
        self.anounce_existance_video()

    def anounce_existance_video(self):
        idslist = ClientsCollection.identifier_list()
        msgdct = {
            "cmd" : "anounce_video_list",
            "identifiers" : idslist 
        }
        self.send_command(json.dumps(msgdct)) 

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
#pcs = set() 

relay = MediaRelay()
audio_relay = MediaRelay()

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

async def index(request):
    print("INDEX")
    f = codecs.open(os.path.join(ROOT, "assets/index.html"), "r", "utf-8")
    content = f.read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    print("JAVASCRIPT")
    f = codecs.open(os.path.join(ROOT, "assets/client.js"), "r", "utf-8")
    content = f.read()
    return web.Response(content_type="application/javascript", text=content)

rgb_flag = FlagVideoStreamTrack(
                [(255,0,0), (0,255,0), (0,0,255)]
            )

def on_datachannel_handler(channel, pc, client):
    print("DATACHANNEL", channel.label)

    if channel.label == "server-message":
        SERVER_MESSAGE_LISTENERS.add(channel)
        client.set_datachannel(channel)
        ClientsCollection.anounce()
        client.send_unique_id()
        ClientsCollection.send_system_chat_message("Новый клиент")

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

    pc = RTCPeerConnection()
    
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    client = Client(pc)
    ClientsCollection.add_client(client)

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
            client = ClientsCollection.client_for_pc(pc)
            ClientsCollection.discard(client)

    recorder = MediaBlackhole()
    @pc.on("track")
    def on_track(track):
        print("TRACK")
        log_info("Track %s received", track.kind)

        if track.kind == "audio":
            print("ADDED AUDIO TRACK")      
            client.set_audio_track(track)
            subscription_track = audio_relay.subscribe(track)
            newtrack = AudioTransformTrack(subscription_track)
            pc.addTrack(newtrack)
        elif track.kind == "video":     
            print("ADDED VIDEO TRACK")      
            newtrack = VideoTransformTrack(
                    relay.subscribe(track, buffered=False), transform=params["video_transform"]
                )
            client.set_video_track(newtrack)
            obj = pc.addTrack(
                newtrack
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
    coros = [cl.pc.close() for cl in ClientsCollection.clients]
    await asyncio.gather(*coros)
    ClientsCollection.clear()

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
    asyncio.run(main(cert_file="assets/cert.pem",key_file="assets/key.pem"))