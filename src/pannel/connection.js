
var DATACHANNEL = null
var PC = null

function negotiate() {
    document.getElementById('state').textContent = "Установка соединения"
    return pc.createOffer().then(function(offer) {
        return pc.setLocalDescription(offer);
    }).then(function() {
        // wait for ICE gathering to complete
        return new Promise(function(resolve) {
            console.log(pc.iceGatheringState)
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                function checkState() {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                }
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(function() {
        var offer = pc.localDescription;
        var codec;

        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
                video_transform:  "none"
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function(response) {
        return response.json();
    }).then(function(answer) {       
        document.getElementById('state').textContent = "Соединение установлено"
        return pc.setRemoteDescription(answer);
    }).catch(function(e) {
        alert(e);
    });
}

function createPeerConnection(use_ice_server) {
    var config = {
        sdpSemantics: 'unified-plan',
    }; 
    if (use_ice_server) 
        config.iceServers = [{url:'stun:stun.l.google.com:19302'},
    ]

    pc = new RTCPeerConnection(config);

    pc.addEventListener('icegatheringstatechange', function() {
        console.log("icegatheringstatechange")
    }, false);
    
    pc.addEventListener('iceconnectionstatechange', function() {
        console.log("iceconnectionstatechange")
    }, false);
    
    pc.addEventListener('signalingstatechange', function() {
        console.log("signalingstatechange")
    }, false);

    return pc;
}

function add_datachannel_for_connection(pc) 
{  
    var parameters = {}
    server_mc = pc.createDataChannel('server-message', parameters);
    server_mc.onmessage = on_command_message
    DATACHANNEL = server_mc
}


function on_command_message(evt) 
{
    dct = JSON.parse(evt.data)
    cmd = dct.cmd
    console.log(evt.data)

    if (cmd == "chat_message") 
    {
        chat_element = document.getElementById("chat")
        chat_element.textContent += dct.identifier + "> " + dct.data + "\r\n"
    }
}

PC = createPeerConnection(true)
add_datachannel_for_connection(PC)

negotiate()