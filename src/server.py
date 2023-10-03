import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import codecs
import sys
import signal
from aiohttp import web
from av import AudioFrame, VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaRelay


from client_collection import ClientCollection
from audio_track import AudioTransformTrack, SilenceAudioStreamTrack
from video_track import VideoTransformTrack, FlagVideoStreamTrack
from client import Client

VIDEO_TRACKS = set()
SERVER_MESSAGE_LISTENERS = set()
REMOTE_TRACKS = list()

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
relay = MediaRelay()
audio_relay = MediaRelay()


def htmlfile(path):
    async def foo(request):
        f = codecs.open(os.path.join(ROOT, path), "r", "utf-8")
        content = f.read()
        return web.Response(content_type="text/html", text=content)
    return foo


def javascript(path):
    async def foo(request):
        f = codecs.open(os.path.join(ROOT, path), "r", "utf-8")
        content = f.read()
        return web.Response(content_type="application/javascript", text=content)
    return foo


async def stylefile(request):
    f = codecs.open(os.path.join(ROOT, "assets/main.css"), "r", "utf-8")
    content = f.read()
    return web.Response(content_type="text/css", text=content)

rgb_flag = FlagVideoStreamTrack(
    [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
)


def on_datachannel_handler(channel, pc, client):
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
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # get argument 'id' from request
    myid = params["myid"]
    print("myid: ", myid)

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    client = Client(pc)
    ClientCollection.add_client(client)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    flag_track = FlagVideoStreamTrack(
        [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    )
    flag_sender = pc.addTrack(flag_track)

    @pc.on("datachannel")
    def on_datachannel(channel):
        on_datachannel_handler(channel, pc, client)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            client = ClientCollection.client_for_pc(pc)
            ClientCollection.discard(client)

    recorder = MediaBlackhole()

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)

        if track.kind == "audio":
            subscription_track = audio_relay.subscribe(track)
            newtrack = AudioTransformTrack(subscription_track)
            client.set_audio_track(newtrack)
            pc.addTrack(newtrack)

        elif track.kind == "video":
            newtrack = VideoTransformTrack(
                relay.subscribe(track, buffered=False), transform=params["video_transform"]
            )
            client.set_video_track(newtrack)

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def offer_control(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    client = Client(pc, is_admin=True)
    ClientCollection.add_client(client)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    @pc.on("datachannel")
    def on_datachannel(channel):
        on_datachannel_handler(channel, pc, client)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            client = ClientCollection.client_for_pc(pc)
            ClientCollection.discard(client)

    await pc.setRemoteDescription(offer)
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
    coros = [cl.pc.close() for cl in ClientCollection.clients.values()]
    await asyncio.gather(*coros)
    ClientCollection.clear()


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
    parser.add_argument(
        "--control-port", type=int, default=9080, help="Port for HTTP control pannel (default: 9080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        cert_file = args.cert_file

    if args.key_file:
        key_file = args.key_file

    ssl_context = ssl.SSLContext()
    ssl_context.load_cert_chain(cert_file, key_file)

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", htmlfile("assets/index.html"))
    app.router.add_get("/client.js", javascript("assets/client.js"))
    app.router.add_get("/runtime.js", javascript("assets/runtime.js"))
    app.router.add_get("/datachannel.js", javascript("assets/datachannel.js"))
    app.router.add_get("/connection.js", javascript("assets/connection.js"))
    app.router.add_get("/main.css", stylefile)
    app.router.add_post("/offer", offer)

    app_control = web.Application()
    app_control.on_shutdown.append(on_shutdown)
    app_control.router.add_get("/", htmlfile("pannel/index.html"))
    app_control.router.add_get(
        "/connection.js", javascript("pannel/connection.js"))
    app_control.router.add_post("/offer", offer_control)

    web_server_task = web._run_app(
        app,
        access_log=None,
        host=args.host,
        port=args.port,
        ssl_context=ssl_context
    )

    web_server_control_pannel = web._run_app(
        app_control,
        access_log=None,
        host=args.host,
        port=args.control_port,
        ssl_context=ssl_context
    )

    await asyncio.gather(
        web_server_task,
        web_server_control_pannel
    )


def set_interrupt_handler(handler):
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


if __name__ == "__main__":
    set_interrupt_handler(lambda a, b: sys.exit(0))
    asyncio.run(main())
