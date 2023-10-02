import traceback


class ClientCollection:
    clients = {}

    def __init__(self):
        pass

    @classmethod
    def add_client(cls, client):
        cls.clients[client.unique_id()] = client

    @classmethod
    def nonadmin_identifier_list(cls):
        return [cl.unique_id() for cl in cls.clients.values() if not cl.is_admin()]
    
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
        if client is None:
            return

        if client.unique_id() in cls.clients:
            del cls.clients[client.unique_id()]

    @classmethod
    def client_for_id(cls, iden):
        return cls.clients[int(iden)]