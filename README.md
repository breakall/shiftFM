# shiftFM

Time-shift FM radio


## Description

This program digitally records FM radio, then generates an RSS feed so the recordings can be played by a podcast player app.



## Hardware

Tested with:
* RTL-SDR v3
* raspberry pi 3b+ running raspbian 10 headless


## Pre-reqs
* Python 3
* [Osmocom RTL-SDR driver](https://osmocom.org/projects/rtl-sdr/wiki/Rtl-sdr)
* ffmpeg (apt install ffmpeg)
* lighttpd (apt install lighttpd)

## Install on Raspberry Pi (automated)
From the repo directory on the Pi:

`sudo -E ./scripts/install_pi.sh`

This installs dependencies, configures a lighttpd instance on port 8088 for MP3/RSS, and starts systemd services.

UI: `http://<pi-ip>:8000`
RSS: `http://<pi-ip>:8088/rss.xml`

To control services:

`sudo systemctl status shiftfm shiftfm-lighttpd`
`sudo systemctl restart shiftfm shiftfm-lighttpd`


## Usage

### Web UI (required)
Run the lightweight scheduler + UI:

`python3 server.py`

Open the UI on your iPhone: `http://<pi-ip>:8000`

Configure schedules, then add the RSS feed to your podcast player:

`http://<pi-ip>:8088/rss.xml` (served by lighttpd)

### Manual execution
Parameters:
`[frequency in MHz] [recording duration in seconds] [name of program]`


Example:

`python3 shiftFM.py 96.1 3600 News`



## RSS feed

The web server generates `rss.xml` automatically after each recording.

Example: if your raspberry pi's IP is 192.168.1.10, add this to your podcast player:

`http://192.168.1.10:8088/rss.xml`


## Notes



## Todo
