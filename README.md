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
* libxslt-dev (for feedgen)
* feedgen (python package for generating feeds)


## Usage
* Parameters: 
`[frequency in MHz] [recording duration in seconds] [name of program]`


### Manual execution
Example: 

`python3 fmshift.py 96.1 3600 News # News_96.1_10-04-2020.mp3` 



### cron jobs

Add these to root's cron (sudo crontab -e):

`# Freakonomics Radio - Saturday, 10a - 11a (3,600 seconds)`

`00 10 * * SAT python3 /home/pi/shiftFM/shiftFM.py 88.9 3600 Freakonomics-Radio >> /home/pi/shiftFM/shiftFM.log 2>&1`

`# generate RSS file every ten minutes`

`0-59/10 * * * * python3 /home/pi/shiftFM/generatefeed.py /home/pi/shiftFM/`

`# copy mp3s to lighttpd folder`

`2-59/10 * * * * cp /home/pi/shiftFM/*.mp3 /var/www/html/`

`# copy RSS file to lighttpd folder`

`3-59/10 * * * * cp /home/pi/shiftFM/rss.xml /var/www/html/`



## RSS feed

The cron jobs above generate the rss.xml file and copy it to the base lighttpd folder.

Get the IP address of your raspberry pi and add the feed URL manually to your podcast player: http://xx.xx.xx.xx/rss.xml

Example: if your raspberry pi's IP is 192.168.1.10 --> http://192.168.1.10/rss.xml


## Notes



## Todo
