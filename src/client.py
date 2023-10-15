
import traceback
from client_collection import ClientCollection
import json
import asyncio
from aiortc.contrib.media import MediaBlackhole, MediaRelay
from audio_track import AccumulateAudioTrack

IDCOUNTER = 0
def generate_uniqueid():
    global IDCOUNTER
    IDCOUNTER += 1
    return IDCOUNTER


class Client:
    def __init__(self, pc, is_admin=False):
        self.pc = pc
        self._is_admin = is_admin
        self.uniqid = generate_uniqueid()
        self._video_track = None
        self._audio_senders = []
        self._video_senders = []
        
        self.relay = MediaRelay()
        self.audio_relay = MediaRelay()

        self.accumulate_audio_track = AccumulateAudioTrack() 
        self.connected_remote_tracks = [-1,-1,-1]

    def set_video_senders(self, senders):
        self._video_senders = senders

    def set_audio_senders(self, senders):
        self._audio_senders = senders

    def send_chat_message(self, fromid, message):
        msgdct = {
            "cmd" : "chat_message",
            "identifier" : fromid,
            "data" : message 
        }
        self.send_command(json.dumps(msgdct)) 

    def is_admin(self):
        return self._is_admin

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
        self.black_hole = MediaBlackhole()
        self.black_hole.addTrack(track)
        self.black_hole_task = self.black_hole.start()
        asyncio.ensure_future(self.black_hole_task)

    def disable_black_hole(self):
        asyncio.ensure_future(self.black_hole.stop())

    def set_audio_track(self, track):
        self._audio_track = track
        self.audio_black_hole = MediaBlackhole()
        self.audio_black_hole.addTrack(track)
        self.audio_black_hole_task = self.audio_black_hole.start()
        asyncio.ensure_future(self.audio_black_hole_task)

    def disable_audio_black_hole(self):
        asyncio.ensure_future(self.audio_black_hole.stop())

    def video_senders(self):
        return self._video_senders

    def audio_senders(self):
        return self._audio_senders

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

    def set_videotrack_for_identifier(self, iden, slot=0):
        try:
            video_cl = ClientCollection.client_for_id(iden)
            if video_cl is None:
                print("Client is not found:", iden)
                return
            if video_cl.is_admin():
                print("Client is admin:", iden)
                return
            self.video_senders()[slot].replaceTrack(video_cl.video_track())
            video_cl.disable_black_hole()
            self.connected_remote_tracks[slot] = iden
        except KeyError as err:
            print("Key is not found:", iden)
            ClientCollection.anounce()
        except:
            print(traceback.format_exc())

    def set_audiotrack_for_identifier(self, iden, slot=0):
        try:
            audio_cl = ClientCollection.client_for_id(iden)
            if audio_cl is None:
                print("Client is not found:", iden)
                return
            if audio_cl.is_admin():
                print("Client is admin:", iden)
                return
            self.audio_senders()[slot].replaceTrack(audio_cl.audio_track())
            audio_cl.disable_audio_black_hole()
        except KeyError as err:
            print("Key is not found:", iden)
            ClientCollection.anounce()
        except:
            print(traceback.format_exc())

    def on_command_message(self, msg):
        print("ExternalCommand:", msg)
        dct = json.loads(msg)
        cmd  = dct["cmd"]
        if cmd == "set_video":
            slot = int(dct["slot"])
            self.set_videotrack_for_identifier(dct["identifier"], slot=slot)
            self.set_audiotrack_for_identifier(dct["identifier"], slot=slot)
        
        if cmd == "chat_message":
            ClientCollection.send_chat_message(self.unique_id(), dct["data"])

        if cmd == "ndi_enable":
            self.enable_ndi(dct["state"] == "ON")

    def anounce(self):
        self.anounce_existance_video()

    def anounce_existance_video(self):
        idslist = ClientCollection.nonadmin_identifier_list()
        msgdct = {
            "cmd" : "anounce_video_list",
            "identifiers" : idslist 
        }
        self.send_command(json.dumps(msgdct)) 