
import traceback
from client_collection import ClientCollection
import json
import asyncio

IDCOUNTER = 0
def generate_uniqueid():
    global IDCOUNTER
    IDCOUNTER += 1
    return IDCOUNTER


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
            video_cl = ClientCollection.client_for_id(iden)
            self.video_sender().replaceTrack(video_cl.video_track())
        except KeyError as err:
            print("Key is not found:", iden)
            ClientCollection.anounce()
        except:
            print(traceback.format_exc())

    def set_audiotrack_for_identifier(self, iden):
        try:
            cl = ClientCollection.client_for_id(iden)
            self.audio_sender().replaceTrack(cl.audio_track())
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
            self.set_videotrack_for_identifier(dct["identifier"])
            self.set_audiotrack_for_identifier(dct["identifier"])
        
        if cmd == "chat_message":
            ClientCollection.send_chat_message(self.unique_id(), dct["data"])

        if cmd == "ndi_enable":
            self.enable_ndi(dct["state"] == "ON")

    def anounce(self):
        self.anounce_existance_video()

    def anounce_existance_video(self):
        idslist = ClientCollection.identifier_list()
        msgdct = {
            "cmd" : "anounce_video_list",
            "identifiers" : idslist 
        }
        self.send_command(json.dumps(msgdct)) 