var pc = null;
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


var time_start = null;
function current_stamp() {
    if (time_start === null) {
        time_start = new Date().getTime();
        return 0;
    } else {
        return new Date().getTime() - time_start;
    }
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
        
        add_datachannel_for_connection(pc)

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
            getCameraSelection();
            getMicrophoneSelection();
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

function videoinput_change() 
{
    cameraOptions = document.getElementById("video_id")
    text = cameraOptions.options[cameraOptions.selectedIndex].text
    console.log(text)

    deviceId = cameraOptions.options[cameraOptions.selectedIndex].value

    // choose video device
    constraints = {
        video: {
            deviceId: { exact: deviceId }
        }
    }
    navigator.mediaDevices.getUserMedia(constraints).then(function(stream) { 
        document.getElementById('video2').srcObject = stream;
        STREAM = stream;
        //SENDERS.forEach((sender) => {
        //    sender.replaceTrack(stream.getVideoTracks()[0])
        //})
        update_resolution_state()
    });
}

function audioinput_change() 
{
    cameraOptions = document.getElementById("audio_id")
    text = cameraOptions.options[cameraOptions.selectedIndex].text
    console.log(text)

    deviceId = cameraOptions.options[cameraOptions.selectedIndex].value

    // choose video device
    constraints = {
        video: {
            deviceId: { exact: deviceId }
        }
    }
    //navigator.mediaDevices.getUserMedia(constraints).then(function(stream) { 
        //document.getElementById('2').srcObject = stream;
        //STREAM = stream;
        //SENDERS.forEach((sender) => {
        //    sender.replaceTrack(stream.getVideoTracks()[0])
        //})
        //update_resolution_state()
    //});
}

// navigator.permissions.query({ name: "camera" }).then((result) => {
//     if (result.state === "granted") {
//         console.log("granted")
//     } else if (result.state === "prompt") {
//         console.log("prompt")
//     }
//   });

const getCameraSelection = async () => {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');
    const options = videoDevices.map(videoDevice => {
      return `<option value="${videoDevice.deviceId}">${videoDevice.label}</option>`;
    });
    cameraOptions = document.getElementById("video_id")
    cameraOptions.innerHTML = options.join('');
  };

  const getMicrophoneSelection = async () => {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'audioinput');
    const options = videoDevices.map(videoDevice => {
      return `<option value="${videoDevice.deviceId}">${videoDevice.label}</option>`;
    });
    microphoneOptions = document.getElementById("audio_id")
    microphoneOptions.innerHTML = options.join('');
  };


open_local_media()


// nosleep
// var noSleep = new NoSleep();

// function enableNoSleep() {
//   noSleep.enable();
//   document.removeEventListener('touchstart', enableNoSleep, false);
// }

// // Enable wake lock.
// // (must be wrapped in a user input event handler e.g. a mouse or touch handler)
// document.addEventListener('touchstart', enableNoSleep, false);