# fmshift.py
# parameters: [frequency in MHz] [recording duration in seconds] [name of program]
# example: python3 fmshift.py 96.1 News---> News_10-04-2020.mp3 
# recording will be terminated after the specified duration
# modified from https://www.linux-magazine.com/Issues/2018/206/Pi-FM-Radio




import subprocess, signal, os, time, sys
from datetime import date

today = date.today()

destination_path = "/home/pi/radioshift/"

def newstation(station):
    global process, stnum





    # create a rtl_fm command line string and insert the new freq
    part1 = "rtl_fm -f "
    part2 = "e6 -M wbfm -s 200k - | ffmpeg -loglevel panic -f s16le -ar 16000 -ac 2 -i - "
    filename = str(sys.argv[3]) + "_" + str(station) + "_" + str(today) + ".mp3"
    cmd = part1 + str(station) + part2 + destination_path + filename
    

    # delete file if already exists

    if os.path.exists(destination_path + filename):
      os.remove(destination_path + filename)    



    # start the new fm connection
    print (cmd)
    process = subprocess.Popen(cmd, stderr=subprocess.STDOUT, shell=True)


# kill fm connection
def kill_process(process):
    if process != 0:
        process = int(subprocess.check_output(["pidof","rtl_fm"] ))
        print ("Process pid = ", process)
        if process != 0:
            os.kill(process,signal.SIGINT)

process = 0
newstation(sys.argv[1])
time.sleep(int(sys.argv[2]))
kill_process(process)
