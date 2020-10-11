# shiftFM

## Hardware

Tested with:
* RTL-SDR v3
* raspberry pi 3b+ running raspbian 10 headless


## Pre-reqs

* [(Osmocom RTL-SDR driver](https://osmocom.org/projects/rtl-sdr/wiki/Rtl-sdr)
* ffmpeg (apt install ffmpeg)
* lighttpd (apt install lighttpd)


## Usage
* Parameters: 
`[frequency in MHz] [recording duration in seconds] [name of program]`


### Manual execution
Example: 

`python3 fmshift.py 96.1 3600 News # News_96.1_10-04-2020.mp3` 



### cron job

`00 11 * * MON,TUE,WED,THU,FRI python3 /home/pi/radioshift/fmshift.py 96.1 3600 News >> /home/pi/fmshift.log 2>&1  #records 96.1MHz for 1 hour every weekday starting at 11 AM`


* run generatefeed.py every ten minutes
* copy mp3 files and rss file every ten minutes


## Notes
* I had to experiment with the rtl_fm sample rate.... based on examples from other 


## Todo
