FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    libopengl-dev \
    libglu1-mesa-dev \
    libglib2.0-0 \
    libgtk2.0-dev

RUN python3 -m pip install numpy
RUN python3 -m pip install opencv-python
RUN python3 -m pip install ndi-python
RUN python3 -m pip install aiohttp aiortc

WORKDIR /app
COPY . .

CMD bash ./start-server.sh