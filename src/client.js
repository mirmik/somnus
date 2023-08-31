// peer connection
var pc = null;

var dataChannelLog = document.getElementById('data-channel')
var systemChannelLog = document.getElementById('system-channel')
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
    console.log("COMMAND:")
    console.log(txt)
    DATACHANNEL.send(txt)
}

function command()
{
    dct = {
        "cmd" : "set_video",
        "identifier" : "1"
    }
    send_command(JSON.stringify(dct))
}

function start() 
{
    pc = createPeerConnection();    
    if (true) {
        //var parameters = JSON.parse(document.getElementById('datachannel-parameters').value);
        var parameters = {}

        dc = pc.createDataChannel('chat', parameters);
        dc.onclose = function() {
            clearInterval(dcInterval);
            dataChannelLog.textContent += '- close\n';
        };
        dc.onopen = function() {
            dataChannelLog.textContent += '- open\n';
            dcInterval = setInterval(function() {
                var message = 'ping ' + current_stamp();
                dataChannelLog.textContent += '> ' + message + '\n';
                dc.send(message);
            }, 1000);
        };
        dc.onmessage = function(evt) {
            dataChannelLog.textContent += '< ' + evt.data + '\n';

            if (evt.data.substring(0, 4) === 'pong') {
                var elapsed_ms = current_stamp() - parseInt(evt.data.substring(5), 10);
                dataChannelLog.textContent += ' RTT ' + elapsed_ms + ' ms\n';
            }
        };


        server_mc = pc.createDataChannel('server-message', parameters);
        server_mc.onopen = function() {
            console.log("SERVER MESSAGE")
        };
        server_mc.onmessage = function(evt) {
            systemChannelLog.textContent += '< ' + evt.data + '\n';
        };
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
    supportedConstrains = navigator.mediaDevices.getSupportedConstraints()
    console.log(supportedConstrains)
    navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {        
       if (!WITHOUT_VIDEO)
           document.getElementById('video').srcObject = stream;
       stream.getTracks().forEach(function(track) {
           console.log("ADD TRACK")
           sender = pc.addTrack(track, stream);
           console.log(sender)
       });
       negotiate()   
    });     
}
