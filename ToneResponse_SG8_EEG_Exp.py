# -*- coding: utf-8 -*-
import random
from typing import List
from matplotlib.pyplot import setp
from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import time
import sys
import numpy as np
from triggers import setParallelData

from meeg import wavhelpers

targetKeys = dict(abort=['q', 'escape'])

# Standard is usually 44.1 or 48 kHz
audioSamplingRate: float = 44100.

# how long should the tone be?
audStimDur_sec: float = 15.

# Fade in/out duration at beginning and end of tone
audStimTaper_sec: float = 0.1

# how long between each tone?
silenceDuration_sec: float = 5.0

# how many repeats of the same tone?
nReps: int = 5

# Set to False to use real EEG
DEBUG: bool = True

def setupTrials(trialList: List[dict], nRep: int) -> List[dict]:
    allTrials: List[dict] = trialList * nRep
    random.shuffle(allTrials)
    return allTrials

# Psychopy window
curMonitor: str = 'testMonitor'
bckColour: str = '#303030'
fullScr: bool = False

expInfo: dict = {
    'subjID': 'test',
    'startIntAbv': -30.0,
    'startIntBlw': -100.0,
    'relTargetVol': 50.,
    'digPort': ['U3', 'LPT', 'Fake']
}

stimListHz: List[int] = [50, 100, 250, 500, 5000, 15000]

# configure Parallel Port triggers for EEG
# 8 bit unsigned integer from 0 to 255
# 0 = no trigger
triggerMap: dict = {
    'start': 1,
    'tone': 2,
    50: 11,
    100: 12,
    250: 13,
    500: 14,
    5000: 15,
    15000: 16
}

dateStr: str = time.strftime("%b%d_%H%M", time.localtime())  # add the current time

# prepare stims
monoChanStrs: List[dict] = []

print("preparing stimuli")
for stimHz in stimListHz:  
    # Save the stimulus as a wav file
    monoChanStr = \
        wavhelpers.load_stimuli(stimHz, audioSamplingRate,
                                audStimDur_sec, audStimTaper_sec, False)
    # Keep track of the file names    
    monoChanStrs.append({'hz': stimHz, 'wavfile': monoChanStr})
print("stimuli prepared")

trialList = setupTrials(monoChanStrs, nReps)

# present a dialogue to change params
dlg = gui.DlgFromDict(expInfo,
                      title='Auditory (dual) staircase',
                      order=[
                          'subjID',
                          'relTargetVol', 'digPort'
                      ])
if not dlg.OK:
    core.quit()  # the user hit cancel so exit



if sys.platform == 'win32':
    import winsound  # noqa

    def playSound(wavfile):
        winsound.PlaySound(wavfile,
                           winsound.SND_FILENAME | winsound.SND_NOWAIT | winsound.SND_ASYNC)

# create window and stimuli
globalClock = core.Clock()  # to keep track of time
trialClock = core.CountdownTimer()

win = visual.Window(monitor=curMonitor,
                    units='deg',
                    fullscr=fullScr,
                    color=bckColour)
fixation = visual.PatchStim(win,
                            color='white',
                            tex=None,
                            mask='gauss',
                            size=0.75)
message1 = visual.TextStim(win, pos=[0, +3], text='Ready...')
message2 = visual.TextStim(win, pos=[0, -3], text='')
message1.draw()
win.flip()
event.waitKeys(keyList=['space', 'enter', 'return'])

message1.setText('Hit a key when ready.')
message2.setText('Then close your eyes, relax, and listen to the sine waves crashing into your eardrums.')

message1.draw()
message2.draw()
fixation.draw()
win.flip()
# check for a keypress
event.waitKeys()

# draw all stimuli
fixation.draw()
win.flip()

globalClock.reset()
setParallelData(triggerMap['start'])
for stim in trialList:
    # play the tone
    print("playing sound at {} Hz".format(stim['hz']))
    setParallelData(triggerMap[stim['hz']])
    playSound(stim['wavfile'])
    try:
        # wait for the duration of the tone
        # and listen for "abort" keypress
        key, time_key = event.waitKeys(maxWait=audStimDur_sec, keyList=targetKeys['abort'])
        if key in targetKeys['abort']:
            win.close()
            core.quit()
    except IndexError:
        # ignore key timeout
        pass
            
    print("done")
    setParallelData(triggerMap[stim['hz']])
    trialClock.reset(silenceDuration_sec)

    while trialClock.getTime() > 0.:
        core.wait(0.010)  # adds some uncertainty too...


# make a text file to save data
fileName = expInfo['subjID'] + '_' + dateStr
dataFile = open(fileName + '.log', 'w')

message1.setText('That\'s it!')
message2.setText('The experiment is over, thanks for participating!')
message1.draw()
message2.draw()
win.flip()

event.waitKeys(keyList=['space', 'enter'])

win.close()
core.quit()
