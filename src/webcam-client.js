var pc = null;

function negotiate() {
    pc.addTransceiver('video', {direction: 'recvonly'});
    pc.addTransceiver('audio', {direction: 'recvonly'});
    return pc.createOffer().then(function(offer) {
        return pc.setLocalDescription(offer);
    }).then(function() {
        // wait for ICE gathering to complete
        return new Promise(function(resolve) {
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
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function(response) {
        return response.json();
    }).then(function(answer) {
        return pc.setRemoteDescription(answer);
    }).catch(function(e) {
        alert(e);
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [{urls: ['stun:stun.l.google.com:19302']}];
    }

    pc = new RTCPeerConnection(config);

    // connect audio / video
    pc.addEventListener('track', function(evt) {
        if (evt.track.kind == 'video') {
            stream = evt.streams[0];
            console.log(stream)
            track = stream.getVideoTracks()[0];
            // get receiver
            receiver = pc.getReceivers().find(function(receiver) {
                return receiver.track.kind == track.kind;
            });


	        // function getMaxBitrates(simulcastMaxBitrates) {
	        // 	let maxBitrates = {
	        // 		high: 900000,
	        // 		medium: 300000,
        	// 		low: 100000,
        	// 	};

        	// 	if(typeof simulcastMaxBitrates !== 'undefined' && simulcastMaxBitrates !== null) {
	        // 		if(simulcastMaxBitrates.high)
	        // 			maxBitrates.high = simulcastMaxBitrates.high;
	        // 		if(simulcastMaxBitrates.medium)
	        // 			maxBitrates.medium = simulcastMaxBitrates.medium;
	        // 		if(simulcastMaxBitrates.low)
	        // 			maxBitrates.low = simulcastMaxBitrates.low;
        	// 	}

        	// 	return maxBitrates;
        	// }


            let parameters = receiver.getParameters;
            console.log(parameters)
            // if(!parameters)
            //     parameters = {};
            // let maxBitrates = getMaxBitrates(track.simulcastMaxBitrates);
            // parameters.encodings = track.sendEncodings || [
            //     { rid: 'h', active: true, maxBitrate: maxBitrates.high },
            //     { rid: 'm', active: true, maxBitrate: maxBitrates.medium, scaleResolutionDownBy: 2 },
            //     { rid: 'l', active: true, maxBitrate: maxBitrates.low, scaleResolutionDownBy: 4 }
            // ];
            // sender.setParameters(parameters);
            console.log(receiver);
            
            document.getElementById('video1').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
        }
    });

    document.getElementById('start').style.display = 'none';
    negotiate();
    document.getElementById('stop').style.display = 'inline-block';
}

function stop() {
    document.getElementById('stop').style.display = 'none';

    // close peer connection
    setTimeout(function() {
        pc.close();
    }, 500);
}
