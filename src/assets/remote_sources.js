

REMOTE_SOURCES = []

function add_remote_source_panel() 
{
    remote_sources_element = document.getElementById("remote_sources")

    // add div
    div = document.createElement("div")
    remote_sources_element.appendChild(div)

    div.appendChild(document.createTextNode("Remote source: "))
    div.appendChild(document.createElement("br"))
    div.className = "remote_source"
    
    // add combobox
    combobox = document.createElement("select")
    div.appendChild(combobox)

    // add video
    video = document.createElement("video")
    video.controls = false
    video.autoplay = true
    video.width = 320
    video.height = 240
    div.appendChild(video)
}

// add_remote_source_panel() 
// add_remote_source_panel() 
// add_remote_source_panel() 