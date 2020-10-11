# shiftFM

## Hardware

Tested with:
* RTL-SDR v3
* raspberry pi 3b+ running raspbian 10 headless


## Pre-reqs

* [(Osmocom RTL-SDR driver](https://osmocom.org/projects/rtl-sdr/wiki/Rtl-sdr)
* ffmpeg (apt install ffmpeg)


## Usage
* Parameters: [frequency in MHz] [recording duration in seconds] [name of program]
* Example: python3 fmshift.py 96.1 3600 News # News_96.1_10-04-2020.mp3 
