

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