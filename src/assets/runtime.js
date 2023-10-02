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