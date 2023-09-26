// peer connection
var pc = null;

var chatChannelLog = document.getElementById('chat')
// var iceConnectionLog = document.getElementById('ice-connection-state')
// var iceGatheringLog = document.getElementById('ice-gathering-state')
// var signalingLog = document.getElementById('signaling-state')

var DATACHANNEL = null
var STREAM = null
var SENDERS = null


var Resolutions = [
    {width: 160, height:120},
    {width: 320, height:180},
    {width: 320, height:240},
    {width: 640, height:360},
    {width: 640, height:480},
    {width: 768, height:576},
    {width: 1024, height:576},
    {width: 1280, height:720},
    {width: 1280, height:768},
    {width: 1280, height:800},
    {width: 1280, height:900},
    {width: 1280, height:1000},
    {width: 1920, height:1080},
    {width: 1920, height:1200},
    {width: 2560, height:1440},
    {width: 3840, height:2160},
    {width: 4096, height:2160}
];

Resolutions.forEach((wh) => {
    document.getElementById("resolutions").options.add(new Option(wh.width.toString() + ":" + wh.height.toString()))
})
document.getElementById("resolutions").options.selectedIndex=2

function negotiate() {
    pc.addTransceiver('video', {direction: 'recvonly'});
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

        //document.getElementById('offer-sdp').textContent = offer.sdp;
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
        console.log("ANSWER")        
        document.getElementById('state').textContent = "Соединение установлено"
        //document.getElementById('answer-sdp').textContent = answer.sdp;
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
    
        // iceServers: [
        // {url:'stun:stun01.sipphone.com'},
        // {url:'stun:stun.ekiga.net'},
        // {url:'stun:stun.fwdnet.net'},
        // {url:'stun:stun.ideasip.com'},
        // {url:'stun:stun.iptel.org'},
        // {url:'stun:stun.rixtelecom.se'},
        // {url:'stun:stun.schlund.de'},
        // {url:'stun:stun1.l.google.com:19302'},
        // {url:'stun:stun2.l.google.com:19302'},
        // {url:'stun:stun3.l.google.com:19302'},
        // {url:'stun:stun4.l.google.com:19302'},
        // {url:'stun:stunserver.org'},
        // {url:'stun:stun.softjoys.com'},
        // {url:'stun:stun.voiparound.com'},
        // {url:'stun:stun.voipbuster.com'},
        // {url:'stun:stun.voipstunt.com'},
        // {url:'stun:stun.voxgratia.org'},
        // {url:'stun:stun.xten.com'},
        // {
        //     url: 'turn:numb.viagenie.ca',
        //     credential: 'muazkh',
        //     username: 'webrtc@live.com'
        // },
        // {
        //     url: 'turn:192.158.29.39:3478?transport=udp',
        //     credential: 'JZEOEt2V3Qb0y27GRntt2u2PAYA=',
        //     username: '28224511:1379330808'
        // },
        // {
        //     url: 'turn:192.158.29.39:3478?transport=tcp',
        //     credential: 'JZEOEt2V3Qb0y27GRntt2u2PAYA=',
        //     username: '28224511:1379330808'
        // }
    ]

    pc = new RTCPeerConnection(config);

    // register some listeners to help debugging
    pc.addEventListener('icegatheringstatechange', function() {
        console.log("icegatheringstatechange")
        // iceGatheringLog.textContent += ' -> ' + pc.iceGatheringState;
    }, false);
    // iceGatheringLog.textContent = pc.iceGatheringState;

    pc.addEventListener('iceconnectionstatechange', function() {
        console.log("iceconnectionstatechange")
        // iceConnectionLog.textContent += ' -> ' + pc.iceConnectionState;
    }, false);
    // iceConnectionLog.textContent = pc.iceConnectionState;

    pc.addEventListener('signalingstatechange', function() {
        console.log("signalingstatechange")
        // signalingLog.textContent += ' -> ' + pc.signalingState;
    }, false);
    // signalingLog.textContent = pc.signalingState;

    // connect audio / video
    pc.addEventListener('track', function(evt) {
        console.log("TRACK")
        console.log(evt)
        if (evt.track.kind == 'video')
        {
            console.log("VIDEO TRACK")
            document.getElementById('video').srcObject = evt.streams[0];
        }
        else
        {
            console.log("AUDIO TRACK")
            document.getElementById('audio2').srcObject = evt.streams[0];
        }
    });

    return pc;
}


var time_start = null;
function current_stamp() {
    if (time_start === null) {
        time_start = new Date().getTime();
        return 0;
    } else {
        return new Date().getTime() - time_start;
    }
}

function send_command(txt) 
{
    DATACHANNEL.send(txt)
}

function command()
{
    cb = document.getElementById("select_video_cb")
    dct = {
        "cmd" : "set_video",
        "identifier" : cb.options[cb.selectedIndex].text
    }
    send_command(JSON.stringify(dct))
}

function control_panel_declare_list(lst) {
    div_element = document.getElementById("server-panel")
    while (div_element.hasChildNodes()) {
        div_element.removeChild(div_element.firstChild)
    }

    lst.forEach((ident) => {
        var iDiv = document.createElement('div');
        iDiv.id = 'block';
        iDiv.className = 'block';
        div_element.appendChild(iDiv)

        var ident_el = document.createElement('p');
        ident_el.textContent = ident
        iDiv.appendChild(ident_el)


        var lbl_el = document.createElement('span');
        lbl_el.textContent = "ndi:"
        iDiv.appendChild(lbl_el)

        var enable_ndi = document.createElement('select');
        enable_ndi.options.add(new Option("OFF"))
        enable_ndi.options.add(new Option("ON"))
        iDiv.appendChild(enable_ndi)

        enable_ndi.addEventListener("change", (event) => {
            state = enable_ndi.options[enable_ndi.selectedIndex].text
            
            dct = {
                "cmd" : "ndi_enable",
                "identifier" : ident,
                "state" : state
            }
            send_command(JSON.stringify(dct))
        })


        var border = document.createElement('p');
        border.textContent = "--------------------"
        iDiv.appendChild(border)
        
    })


}

function on_command_message(evt) 
{
    dct = JSON.parse(evt.data)
    cmd = dct.cmd
    console.log(evt.data)
    
    if (cmd == "anounce_video_list") 
    {
        cb = document.getElementById("select_video_cb")
        while (cb.options.length > 0) {                
            cb.remove(0);
        }  
        console.log(cb.options)
        dct.identifiers.forEach((i) => {
            cb.options.add(new Option(i))
        })
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

function add_media_tracks_to_connection(stream) 
{
    senders = []
    stream.getTracks().forEach(function(track) {
        sender = pc.addTrack(track, stream);
        senders.push(sender)
    });
    return senders
}

function start_connection() 
{
    try {
        document.getElementById('state').textContent = "Соединение устанавливается"
        use_ice_server = document.getElementById("use_ice_server").checked
        pc = createPeerConnection(use_ice_server);    
        var parameters = {}
        server_mc = pc.createDataChannel('server-message', parameters);
        server_mc.onmessage = on_command_message
        DATACHANNEL = server_mc

        SENDERS = add_media_tracks_to_connection(STREAM);
        negotiate().then(function() {
            document.getElementById('remote_section').style.display = 'inline-block';
        });

        // disable connection control elements
        document.getElementById('connection_section').style.display = 'none';
    }
    catch (e) {
        error_state(e)
    }
}

function disable_camera()
{
    STREAM.getVideoTracks().forEach(function(track) {
        track.enabled = false;
    });
}

function enable_camera()
{
    STREAM.getVideoTracks().forEach(function(track) {
        track.enabled = true;
    });
}

function disable_mic() {
    STREAM.getAudioTracks().forEach(function(track) {
        track.enabled = false;
    });
}

function enable_mic() {
    STREAM.getAudioTracks().forEach(function(track) {
        track.enabled = true;
    });
}

function change_resolution(w, h)
{
    STREAM.getVideoTracks()[0].applyConstraints(
        {
            width: w,
            height: h
        }
    );
    update_resolution_state()
}

function update_resolution_state()
{
    settings = STREAM.getVideoTracks()[0].getSettings()
    w = settings.width
    h = settings.height

    console.log(w, h)
    document.getElementById("resolution_state").textContent = w.toString() + ":" + h.toString()
}

function get_resolution()
{
    settings = STREAM.getVideoTracks()[0].getSettings()
    console.log(settings)
    return settings.width.toString() + ":" + settings.height.toString()
}

function change_resolution_button()
{
    res = document.getElementById("resolutions")
    wh = res.options[res.selectedIndex].text.split(":")
    w = parseInt(wh[0])
    h = parseInt(wh[1])
    STREAM.getVideoTracks()[0].applyConstraints(
        {
            width: w,
            height: h
        }
    ).then(() => {
    update_resolution_state();
    });
}



function error_state(exception)
{
    document.getElementById('errorlog').textContent = exception
    console.log(exception)
}

function exception_simulate()
{
    throw "Exception"
}

function open_local_media() 
{
    try {
        var constraints = {
            audio: true,
            video: true
        };
        navigator.mediaDevices.getUserMedia(constraints).then(function(stream) { 
            document.getElementById('video2').srcObject = stream;
            STREAM = stream;
            audio_amplitude();
            update_resolution_state()
        });  
    }
    catch (e) {
        error_state(e)
    }
}

open_local_media()

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







// var left = 0;
// var right = ResolutionsToCheck.length;
// var selectedWidth;
// var selectedHeight;
// var mid;

// function FindMaximum_WidthHeight_ForCamera()
// {
//     //console.log("left:right = ", left, ":", right);
//     if(left > right)
//     {
//         console.log("Selected Height:Width = ", selectedWidth, ":", selectedHeight);
//         return;
//     }

//     mid = Math.floor((left + right) / 2);

//     var temporaryConstraints = {
//         "audio": true,
//         "video": {
//         "mandatory": {
//             "minWidth": ResolutionsToCheck[mid].width,
//             "minHeight": ResolutionsToCheck[mid].height,
//             "maxWidth": ResolutionsToCheck[mid].width,
//             "maxHeight": ResolutionsToCheck[mid].height
//             },
//             "optional": []
//         }
//     }

//     navigator.mediaDevices.getUserMedia(temporaryConstraints).then(checkSuccess).catch(checkError);
// }

// function checkSuccess(stream)
// {
//     console.log("Success for --> " , mid , " ", ResolutionsToCheck[mid]);
//     selectedWidth = ResolutionsToCheck[mid].width;
//     selectedHeight = ResolutionsToCheck[mid].height;

//     left = mid+1;

//     for (let track of stream.getTracks()) 
//     { 
//         track.stop()
//     }

//     FindMaximum_WidthHeight_ForCamera();
// }

// function checkError(error)
// {
//     console.log("Failed for --> " + mid , " ", ResolutionsToCheck[mid],  " ", error);
//     right = mid-1;
//     FindMaximum_WidthHeight_ForCamera();
// }

// console.log("HEERERERER")
// FindMaximum_WidthHeight_ForCamera();
// console.log("HEERERERER 222")


function audio_amplitude() {
    audio_signal = STREAM.getAudioTracks()[0]
    audio_ctx = new AudioContext();
    analyser = audio_ctx.createAnalyser();
    microphone = audio_ctx.createMediaStreamSource(STREAM);
    javascriptNode = audio_ctx.createScriptProcessor(2048, 1, 1);
    
    analyser.smoothingTimeConstant = 0.8;
    analyser.fftSize = 1024;

    microphone.connect(analyser);
    analyser.connect(javascriptNode);
    javascriptNode.connect(audio_ctx.destination);
    javascriptNode.onaudioprocess = function() {
        var array = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(array);
        var values = 0;

        var length = array.length;
        for (var i = 0; i < length; i++) {
            values += (array[i]);
        }

        var average = values / length;
        document.getElementById("audio-amplitude").textContent = Math.round(average)
    }
}