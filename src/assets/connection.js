AUDIO_STREAM = null

function negotiate() {
    pc.addTransceiver('video', {direction: 'recvonly'});
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

var i = 0

function createPeerConnection(use_ice_server) {
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
             if (i == 0)
             {      
                 i = 1;
                 set_video_to_remote_source(0, evt.streams[0])
            }
            else  if (i == 1)
            {
                i = 2;
                set_video_to_remote_source(0, new MediaStream([evt.streams[0].getTracks()[2]]))
                set_video_to_remote_source(1, new MediaStream([evt.streams[0].getTracks()[1]]))
            }
            else  if (i == 2)
            {
                i = 0;
                set_video_to_remote_source(0, new MediaStream([evt.streams[0].getTracks()[3]]))
                set_video_to_remote_source(1, new MediaStream([evt.streams[0].getTracks()[2]]))
                set_video_to_remote_source(2, new MediaStream([evt.streams[0].getTracks()[1]]))
            }
        }
        else
        {
            console.log("AUDIO TRACK")
            document.getElementById('audio_play').srcObject = evt.streams[0];
            AUDIO_STREAM = evt.streams[0];
        }
    });

    return pc;
}

function disable_sound_play()
{
    console.log("disable_sound_play")
    document.getElementById('audio_play').srcObject = null;
    document.getElementById('audio_play').pause();
}

function enable_sound_play()
{
    console.log("enable_sound_play")
    document.getElementById('audio_play').srcObject = AUDIO_STREAM;
}