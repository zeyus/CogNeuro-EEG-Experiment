# -*- coding: utf-8 -*-
# Set to False to use real EEG / parallel port
DEBUG: bool = False
DATA_DIR: str = './data/'
STIM_DIR: str = './stims/'

import datetime
from glob import glob
import os
import random
from typing import List
from psychopy import core, visual, gui, event
import sys
import numpy as np
if not DEBUG:
    from triggers import setParallelData

from meeg import wavhelpers

targetKeys = dict(abort=['q', 'escape'])

# how many seconds we have available
experimentTimeMax_sec: int = 600 / 2 # 5 minutes eyes open, 5 minutes eyes closed

# Standard is usually 44.1 or 48 kHz
audioSamplingRate: float = 44100.

# how long should the tone be
requiredAudStimDur_sec: float = 15.

# how many times we play the tone for requiredAudStimDur_sec
nRepsRequired: int = 1

# for the other trials, this is the minimum duration to play the tone
audStimDurMin_sec: float = 1.0

# for the other trials, this is the maximum duration to play the tone
audStimDurMax_sec: float = 2.5

# Fade in/out duration at beginning and end of tone
audStimTaper_sec: float = 0.1

# how long between each tone?
silenceDurationMin_sec: float = 0.8
silenceDurationMax_sec: float = 2.5


def calculateDuration(stimListExperiment: List[dict]) -> float:
    return sum(stim['duration'] + stim['silence_duration'] for stim in stimListExperiment)


# Psychopy window
curMonitor: str = 'testMonitor'
bckColour: str = '#303030'
fullScr: bool = False

expInfo: dict = {
    'subjID': 'test',
}

# configure Parallel Port triggers for EEG
# 8 bit unsigned integer from 0 to 255
# 0 = no trigger
# 'open' = eyes open condition
# 'closed' = eyes closed condition
triggerMap: dict = {
    50: {'open': 11, 'closed': 21},
    100: {'open': 12, 'closed': 22},
    250: {'open': 13, 'closed': 23},
    500: {'open': 14, 'closed': 24},
    2500: {'open': 15, 'closed': 25},
    5000: {'open': 16, 'closed': 26},
    7500: {'open': 17, 'closed': 27},
    15000: {'open': 18, 'closed': 28},
}

# list of all tones we want to play
stimListHz: List[int] = triggerMap.keys()
nStims: int = len(stimListHz)
print("Number of unique frequencies: ", nStims)

# extra triggers
triggerMap['stop'] = 0
triggerMap['start'] = 1
triggerMap['open'] = 10
triggerMap['closed'] = 20


# clean up any old stimuli
oldStimuli = glob(STIM_DIR + '*.wav')
print("Removing old stimuli...")
for oldStim in oldStimuli:
    # we'll keep the 15 second ones
    if oldStim.endswith('15.00s.wav'):
        continue
    print("Removing old stimulus: ", oldStim)
    os.remove(oldStim)

# just generate a bunch of lengths for the silence, we won't use 1000 but we can just read along the list
silenceDurations_sec: List[float] = np.random.uniform(silenceDurationMin_sec, silenceDurationMax_sec, 1000).round(2).tolist()

# get random silence durations
silences: List[float] = silenceDurations_sec[-nStims:]

# removed used random silence durations from list
del silenceDurations_sec[-nStims:]

# start off by adding the required durations for each tone to the list
stimListExperiment: List[dict] = [{'stim': stimHz, 'duration': dur, 'silence_duration': sil} for stimHz, dur, sil in zip(stimListHz, [requiredAudStimDur_sec] * nStims, silences)]

# now calculate used time
expTimeUsed_sec: float = calculateDuration(stimListExperiment)


# now we will add in as many additional sets of tones as we can to fill the time
while expTimeUsed_sec < experimentTimeMax_sec:
    toneDuration_sec: float = round(random.uniform(audStimDurMin_sec, audStimDurMax_sec), 2)
    # get random silence durations
    silences: List[float] = silenceDurations_sec[-nStims:]
    # removed used random silence durations from list
    del silenceDurations_sec[-nStims:]

    # create a new set of stimuli, each tone played for the same duration
    # but with random silence lengths
    stimSet: List[dict] = [{'stim': stimHz, 'duration': dur, 'silence_duration': sil} for stimHz, dur, sil in zip(stimListHz, [toneDuration_sec] * nStims, silences)]

    # calculate how long this new set will run for
    stimSetDuration_sec: float = calculateDuration(stimSet)

    # if the current running time plus the set is too long, we will stop
    if expTimeUsed_sec + stimSetDuration_sec > experimentTimeMax_sec:
        break

    # otherwise we add it to the list of stimuli
    stimListExperiment.extend(stimSet)

    # update running time
    expTimeUsed_sec += stimSetDuration_sec

# times 2 because we are doing both eyes open and closed
print("Total experiment time: ", expTimeUsed_sec * 2)

print("preparing stimuli")
for i, stim in enumerate(stimListExperiment):
    # Save the stimulus as a wav file
    monoChanStr = \
        wavhelpers.load_stimuli(stim['stim'], audioSamplingRate,
                                stim['duration'], audStimTaper_sec, False)
    # Keep track of the file names
    stimListExperiment[i]['filename'] = monoChanStr
    
print("stimuli prepared")

# create a copy for the eyes closed condition
stimListExperiment_closed = stimListExperiment.copy()

# randomize order
random.shuffle(stimListExperiment)
random.shuffle(stimListExperiment_closed)

print("final experiment structure: ")
print("Eyes open:")
print(' ->\n'.join(['{}Hz ({}s), silence ({}s)'.format(x['stim'], x['duration'], x['silence_duration']) for x in stimListExperiment]))
print("Eyes closed:")
print(' ->\n'.join(['{}Hz ({}s), silence ({}s)'.format(x['stim'], x['duration'], x['silence_duration']) for x in stimListExperiment_closed]))


# present a dialogue to change params
dlg = gui.DlgFromDict(expInfo,
                      title='Tone Differentiation',
                      order=['subjID'])
if not dlg.OK:
    core.quit()  # the user hit cancel so exit

# save the experiment structure to a log file
# make a text file to save data
fileName = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
dataFile = open(DATA_DIR + fileName + '.csv', 'w')

# write header
dataFile.write('subjID,stim (Hz),stim_fade,stim_duration,stim_silence_duration,eeg_tag,condition\n')
# write data
for stim in stimListExperiment:
    dataFile.write('{},{},{},{},{},{},{}\n'.format(expInfo['subjID'],
                                                    stim['stim'],
                                                    audStimTaper_sec,
                                                    stim['duration'],
                                                    stim['silence_duration'],
                                                    triggerMap[stim['stim']]['open'],
                                                    'open'))
for stim in stimListExperiment_closed:
    dataFile.write('{},{},{},{},{},{},{}\n'.format(expInfo['subjID'],
                                                    stim['stim'],
                                                    audStimTaper_sec,
                                                    stim['duration'],
                                                    stim['silence_duration'],
                                                    triggerMap[stim['stim']]['closed'],
                                                    'closed'))
dataFile.close()

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
key = event.waitKeys(keyList=['space', 'enter', 'return'] + targetKeys['abort'])
if key in targetKeys['abort']:
    win.close()
    core.quit()

message1.setText('Hit a key when ready.')
message2.setText('Please keep your eyes OPEN for the first part of this experiment and try to look at the dot on the screen.')

message1.draw()
message2.draw()
fixation.draw()
win.flip()
# check for a keypress
key = event.waitKeys(keyList=['space', 'enter', 'return'] + targetKeys['abort'])
if key in targetKeys['abort']:
    win.close()
    core.quit()
# draw all stimuli
fixation.draw()
win.flip()

globalClock.reset()
if not DEBUG:
    setParallelData(triggerMap['start'])
# eyes open loop
for stim in stimListExperiment:
    # play the tone
    print("playing sound at {} Hz".format(stim['stim']))
    playSound(stim['filename'])
    if not DEBUG:
        setParallelData(triggerMap[stim['stim']]['open'])
    try:
        # wait for the duration of the tone
        # and listen for "abort" keypress
        key, time_key = event.waitKeys(maxWait=stim['duration'], keyList=targetKeys['abort'])
        if key in targetKeys['abort']:
            win.close()
            core.quit()
    except IndexError:
        # ignore key timeout
        pass
    except TypeError:
        # ignore key timeout
        pass
            
    print("done")
    if not DEBUG:
        setParallelData(triggerMap['stop'])
    trialClock.reset(stim['silence_duration'])

    while trialClock.getTime() > 0.:
        core.wait(0.010)  # adds some uncertainty too...

message1.setText('Hit a key when ready.')
message2.setText('Please keep your eyes CLOSED for the second part of this experiment. You will be informed when it is complete.')

message1.draw()
message2.draw()
fixation.draw()
win.flip()
# check for a keypress
key = event.waitKeys(keyList=['space', 'enter', 'return'] + targetKeys['abort'])
if key in targetKeys['abort']:
    win.close()
    core.quit()
# draw all stimuli
fixation.draw()
win.flip()

globalClock.reset()
if not DEBUG:
    setParallelData(triggerMap['start'])

# eyes closed loop
for stim in stimListExperiment_closed:
    # play the tone
    print("playing sound at {} Hz".format(stim['stim']))
    playSound(stim['filename'])
    if not DEBUG:
        setParallelData(triggerMap[stim['stim']]['closed'])
    try:
        # wait for the duration of the tone
        # and listen for "abort" keypress
        key, time_key = event.waitKeys(maxWait=stim['duration'], keyList=targetKeys['abort'])
        if key in targetKeys['abort']:
            win.close()
            core.quit()
    except IndexError:
        # ignore key timeout
        pass
    except TypeError:
        # ignore key timeout
        pass
            
    print("done")
    if not DEBUG:
        setParallelData(triggerMap['stop'])
    trialClock.reset(stim['silence_duration'])

    while trialClock.getTime() > 0.:
        core.wait(0.010)  # adds some uncertainty too...




message1.setText('That\'s it!')
message2.setText('The experiment is over, thanks for participating!')
message1.draw()
message2.draw()
win.flip()

event.waitKeys(keyList=['space', 'enter'])

win.close()
core.quit()
