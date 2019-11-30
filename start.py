import sys
import spotipy
import spotipy.util as util
import time, threading

from qhue import Bridge
from qhue import create_new_username
import discoverhue

import random

class BeatTicker():

    def __init__(self, username = None , hueTicker = None, offset = -0.2):
        self.hueTicker = hueTicker
        if username == None:
            username = input("username")
        self.scope = 'user-read-currently-playing'
        self.token = util.prompt_for_user_token(username, self.scope, client_id='client_id',client_secret='secret',redirect_uri='http://m-3.me/')
        self.currPlaying = None

        self.offset = offset

        self.phases = {}

        if self.token:
            self.sp = spotipy.Spotify(auth=self.token)
            self.updateTrack()
        else:
            print ("Can't get token for", username)

    def beatTick(self, song):
        if (self.currPlaying == song):
            self.hueTicker.baseTick(song , self.name)

    def showBeats(self, beats, timestamp):
        seconds = timestamp / 1000
        after = []
        song = self.currPlaying
        offset = self.offset
        for beat in beats:
            if beat["start"] > seconds:
                after.append((beat["start"] - seconds + offset, beat["duration"]))
                start = beat["start"]
                threading.Timer(beat["start"] - seconds+ offset, lambda: self.beatTick(song)).start()
        self.hueTicker.setPhase("superchill")
        for startseconds,phase in self.phases.items():
            if startseconds > seconds:
                if phase == "superchill": threading.Timer(startseconds - seconds + offset, lambda: self.hueTicker.setPhase("superchill")).start()
                if phase == "chill": threading.Timer(startseconds - seconds+ offset, lambda: self.hueTicker.setPhase("chill")).start()
                if phase == "superhard": threading.Timer(startseconds - seconds+ offset, lambda: self.hueTicker.setPhase("superhard")).start()
                if phase == "hard": threading.Timer(startseconds - seconds+ offset, lambda: self.hueTicker.setPhase("hard")).start()
                if phase == "normal": threading.Timer(startseconds - seconds+ offset, lambda: self.hueTicker.setPhase("normal")).start()


    def getInformation(self,songid , currtimestamp):
        audiofeatures = self.sp.audio_features(songid)
        audioanalysis = self.sp.audio_analysis(songid)
        beats = audioanalysis["beats"]
        self.hueTicker.setBPS(audioanalysis["track"]["tempo"])
        self.phases = {0: "superchill"}
        print("energy" , audiofeatures[0]["energy"])
        for phase in audioanalysis["sections"]:
            if (phase["tempo"] <= audioanalysis["track"]["tempo"] - 20 or phase["loudness"] <= audioanalysis["track"]["loudness"] - 2.5) and audiofeatures[0]["energy"] <0.9:
                self.phases[phase["start"]] = "superchill"
            elif (phase["tempo"] <= audioanalysis["track"]["tempo"] - 5 or phase["loudness"] <= audioanalysis["track"]["loudness"] - 1.5) and audiofeatures[0]["energy"] <0.9:
                self.phases[phase["start"]] = "chill"
            elif phase["tempo"] >= audioanalysis["track"]["tempo"] + 10 or phase["loudness"] >= audioanalysis["track"]["loudness"] + 2.5:
                self.phases[phase["start"]] = "superhard"
            elif phase["tempo"] >= audioanalysis["track"]["tempo"] + 2.5 or phase["loudness"] >= audioanalysis["track"]["loudness"] + 1.5 or (audiofeatures[0]["energy"] >0.9 and phase["loudness"] >= audioanalysis["track"]["loudness"] + 1):
                self.phases[phase["start"]] = "hard"
            else:
                self.phases[phase["start"]] = "normal"

        self.showBeats(beats , currtimestamp)

            
    def updateTrack(self):
        data = self.sp.current_user_playing_track()
        #print(data["progress_ms"])
        if self.currPlaying != data["item"]["id"]:
            self.currPlaying = data["item"]["id"]
            self.name = data["item"]["name"]
            print ("New song detected" , data["item"]["name"])
            self.getInformation(self.currPlaying , data["progress_ms"])
        threading.Timer(1, self.updateTrack).start()



class HueSync():

    def __init__(self , ip , usegroup = "Keller" , username = None):
        if username is None: username = create_new_username(ip)
        print(username)
        self.b = Bridge(ip , username)

        self.bps = 100

        groups = self.b.groups()
        self.group = None
        for group in range(1,len(self.b.groups()) + 1):
            if (usegroup == self.b.groups()[str(group)]["name"]):
                self.lights = self.b.groups()[str(group)]["lights"]
                self.group = str(group)
                print("Using lights in",usegroup,self.lights)
                break

        self.counter = 0
        self.max = len(self.lights)-1
        self.phase = "chill"
        
        pass

    def setBPS(self, bps):
        self.bps = bps

    def setPhase(self, phase):
        self.phase = phase
        print("New phase" , phase)
    
    def baseTick(self , songid , name):
        light = self.counter
        self.b.lights(int(self.lights[light]), 'state', on=True, bri=255, hue=random.randint(0,65535), transitiontime=4)
        if self.phase == "superchill":
            self.b.lights(int(self.lights[light]), 'state', on=True, bri=80, hue=random.randint(0,65535), transitiontime=3)
        if self.phase == "chill":
            self.b.lights(int(self.lights[light]), 'state', on=True, bri=120, hue=random.randint(0,65535), transitiontime=2)
        if self.phase == "normal":
            self.b.lights(int(self.lights[light]), 'state', on=True, bri=190, hue=random.randint(0,65535), transitiontime=1)
            threading.Timer(self.bps/200, lambda: self.b.lights(int(self.lights[light]), 'state', on=False , transitiontime=0)).start()
        if self.phase == "hard":
            self.b.lights(int(self.lights[light]), 'state', on=True, bri=255, hue = random.randint(0,65535), transitiontime=0)
            threading.Timer(self.bps/200, lambda: self.b.lights(int(self.lights[light]), 'state', on=False , transitiontime=0)).start()
        if self.phase == "superhard":
            self.b.lights(int(self.lights[light]), 'state', on=True, bri=255, ct=154, transitiontime=0)
            threading.Timer(self.bps/1000, lambda: self.b.lights(int(self.lights[light]), 'state', on=False , transitiontime=0)).start()
        if light == self.max:
            self.counter = 0
        else: self.counter += 1

##found = discoverhue.find_bridges()
##ip = None
##for bridge in found:
##    ip = found[bridge].replace("http://" , "")
##    ip = ip.replace(":80/" , "")
##    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge]))
h = HueSync("192.168.1.164" , username = "-q6yVRkfE6Q2PPZlfpuFUksw4DoS3wPLl7MIe0YZ")
b = BeatTicker("mrmemes" , h)
