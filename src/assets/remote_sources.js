

REMOTE_SOURCES = []

function request_media_channel_button_click(num, cb)
{
    dct = {
        "cmd" : "set_video",
        "identifier" : cb.options[cb.selectedIndex].text,
        "slot": num
    }
    send_command(JSON.stringify(dct))
}

function add_remote_source_panel() 
{
    remote_sources_element = document.getElementById("remote_sources")

    index = REMOTE_SOURCES.length

    // add div
    div = document.createElement("div")
    div.className = "remote_source"
    remote_sources_element.appendChild(div)

    control_div = document.createElement("div")
    control_div.appendChild(document.createTextNode("Remote source: "))
    control_div.appendChild(document.createElement("br"))
    
    // add combobox
    combobox = document.createElement("select")
    control_div.appendChild(combobox)

    // add button
    button = document.createElement("button")
    button.combobox = combobox
    button.index = index
    button.textContent = "Connect"
    button.addEventListener("click", (event) => {
        index = event.target.index
        combobox = event.target.combobox
        request_media_channel_button_click(index, combobox)
    }) 
    control_div.appendChild(button)
    div.appendChild(control_div)    

    // add video
    videodiv = document.createElement("div")
    video = document.createElement("video")
    videodiv.appendChild(video)
    video.controls = false
    video.autoplay = true
    video.mute = true
    video.width = 320
    video.height = 240
    div.appendChild(videodiv)

    REMOTE_SOURCES.push({
        "div" : div,
        "combobox" : combobox,
        "video" : video
    })
}

function set_remote_identifiers_to_comboboxes(identifiers)
{
    REMOTE_SOURCES.forEach((rs) => {
        combobox = rs.combobox
        while (combobox.options.length > 0) {                
            combobox.remove(0);
        }  
        identifiers.forEach((i) => {
            combobox.options.add(new Option(i))
        })
    })
}

function set_video_to_remote_source(num, stream)
{
    REMOTE_SOURCES[num].video.srcObject = stream
}




function createPeerConnection_2(use_ice_server) {
    var config = {
        sdpSemantics: 'unified-plan',
    }; 
    if (use_ice_server) 
        config.iceServers = [    
        {url:'stun:stun3.l.google.com:19302'},
        {url:'stun:stun.voipbuster.com'},
        {url:'stun:stun4.l.google.com:19302'},
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

    pc.addEventListener('track', function(evt) {
        if (evt.track.kind == 'video')
        {
            console.log("VIDEO TRACK 2")
        }
        else
        {
            console.log("AUDIO TRACK 2")
        }
    });

    return pc;
}



function negotiate_2(pc) {
    pc.addTransceiver('video', {send: true, receive: true});
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
                video_transform:  "none",
                myid: document.getElementById("username").value,
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

// task = open_local_media()
// task . then(() => {
//     pcc = createPeerConnection_2(false)
//     add_datachannel_for_connection(pcc)
//     //SENDERS = add_media_tracks_to_connection(pcc, STREAM);
//     negotiate_2(pcc)
// })