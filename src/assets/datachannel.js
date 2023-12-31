
var chatChannelLog = document.getElementById('chat')
var DATACHANNEL = null

function send_command(txt) 
{
    DATACHANNEL.send(txt)
}

function add_datachannel_for_connection(pc) 
{  
    var parameters = {}
    server_mc = pc.createDataChannel('server-message', parameters);
    server_mc.onmessage = on_command_message
    DATACHANNEL = server_mc
}

function announce_video_list(identifiers)
{
    set_remote_identifiers_to_comboboxes(identifiers)
}

function on_command_message(evt) 
{
    dct = JSON.parse(evt.data)
    cmd = dct.cmd
    console.log(evt.data)
    
    if (cmd == "anounce_video_list") 
    {
        announce_video_list(dct.identifiers)
        control_panel_declare_list(dct.identifiers)
    }

    if (cmd == "set_unique_id") 
    {
        console.log("SET_UNIQUE_ID")
        uniqid = dct.identifier
        el = document.getElementById("my-identifier")
        el.textContent = uniqid
    }

    if (cmd == "chat_message") 
    {
        chat_element = document.getElementById("chat")
        chat_element.textContent += dct.identifier + "> " + dct.data + "\r\n"
    }
}

// CHAT

var input = document.getElementById("chatinput");
input.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      text = input.value
      if (text == "")
        return;
      console.log(text)
      dct = {
            "cmd" : "chat_message",
            "data" : text
        }
       send_command(JSON.stringify(dct))
       text = input.value = ""
    }
  }); 
