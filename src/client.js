// peer connection
var pc = null;

var chatChannelLog = document.getElementById('chat')
var iceConnectionLog = document.getElementById('ice-connection-state')
var iceGatheringLog = document.getElementById('ice-gathering-state')
var signalingLog = document.getElementById('signaling-state')

let WITHOUT_VIDEO = true;
var DATACHANNEL = null

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

        document.getElementById('offer-sdp').textContent = offer.sdp;
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
        document.getElementById('answer-sdp').textContent = answer.sdp;
        return pc.setRemoteDescription(answer);
    }).catch(function(e) {
        alert(e);
    });
}

function createPeerConnection() {
    var config = {
        sdpSemantics: 'unified-plan',
        iceServers: [{urls: ['stun:stun.l.google.com:19302']}]
    };
    config.iceServers = [{urls: ['stun:stun.l.google.com:19302']}];
        

    pc = new RTCPeerConnection(config);

    // register some listeners to help debugging
    pc.addEventListener('icegatheringstatechange', function() {
        console.log("icegatheringstatechange")
        iceGatheringLog.textContent += ' -> ' + pc.iceGatheringState;
    }, false);
    iceGatheringLog.textContent = pc.iceGatheringState;

    pc.addEventListener('iceconnectionstatechange', function() {
        console.log("iceconnectionstatechange")
        iceConnectionLog.textContent += ' -> ' + pc.iceConnectionState;
    }, false);
    iceConnectionLog.textContent = pc.iceConnectionState;

    pc.addEventListener('signalingstatechange', function() {
        console.log("signalingstatechange")
        signalingLog.textContent += ' -> ' + pc.signalingState;
    }, false);
    signalingLog.textContent = pc.signalingState;

    // connect audio / video
    pc.addEventListener('track', function(evt) {
        console.log("TRACK")
        console.log(evt)
        if (evt.track.kind == 'video')
            document.getElementById('video').srcObject = evt.streams[0];
        else
            document.getElementById('audio').srcObject = evt.streams[0];
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

function start() 
{
    pc = createPeerConnection();    
    if (true) {
        //var parameters = JSON.parse(document.getElementById('datachannel-parameters').value);
        var parameters = {}
        server_mc = pc.createDataChannel('server-message', parameters);
        server_mc.onmessage = on_command_message
        DATACHANNEL = server_mc
    }    

    console.log("start")
    var constraints = {
        audio: false,
        video: {
            width: 640,
            height: 480
        }
    };

    navigator.mediaDevices.enumerateDevices().then((devices)=>{
        console.log(devices)
    })

    navigator.mediaDevices.getUserMedia(constraints).then(function(stream) { 
        console.log(stream)        
       if (!WITHOUT_VIDEO)
           document.getElementById('video').srcObject = stream;
       stream.getTracks().forEach(function(track) {
           console.log("ADD TRACK")
           console.log(track)
           console.log(track.getConstraints())
           console.log(track.getSettings())
           sender = pc.addTrack(track, stream);
           console.log(sender)
       });
       negotiate()   
    });     
}

start()

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






  var ResolutionsToCheck = [
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

var left = 0;
var right = ResolutionsToCheck.length;
var selectedWidth;
var selectedHeight;
var mid;

function FindMaximum_WidthHeight_ForCamera()
{
    //console.log("left:right = ", left, ":", right);
    if(left > right)
    {
        console.log("Selected Height:Width = ", selectedWidth, ":", selectedHeight);
        return;
    }

    mid = Math.floor((left + right) / 2);

    var temporaryConstraints = {
        "audio": true,
        "video": {
        "mandatory": {
            "minWidth": ResolutionsToCheck[mid].width,
            "minHeight": ResolutionsToCheck[mid].height,
            "maxWidth": ResolutionsToCheck[mid].width,
            "maxHeight": ResolutionsToCheck[mid].height
            },
            "optional": []
        }
    }

    navigator.mediaDevices.getUserMedia(temporaryConstraints).then(checkSuccess).catch(checkError);
}

function checkSuccess(stream)
{
    console.log("Success for --> " , mid , " ", ResolutionsToCheck[mid]);
    selectedWidth = ResolutionsToCheck[mid].width;
    selectedHeight = ResolutionsToCheck[mid].height;

    left = mid+1;

    for (let track of stream.getTracks()) 
    { 
        track.stop()
    }

    FindMaximum_WidthHeight_ForCamera();
}

function checkError(error)
{
    console.log("Failed for --> " + mid , " ", ResolutionsToCheck[mid],  " ", error);
    right = mid-1;
    FindMaximum_WidthHeight_ForCamera();
}

console.log("HEERERERER")
FindMaximum_WidthHeight_ForCamera();
console.log("HEERERERER 222")
