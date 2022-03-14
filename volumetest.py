
import winsound
from meeg import wavhelpers

def playSound(wavfile):
    winsound.PlaySound(wavfile,
                        winsound.SND_FILENAME | winsound.SND_NOWAIT)

testTones = [50, 5000, 15000]
testDuration = 5.
testFade = 0.1
testSR = 44100.


for tone in testTones:
    monoChanStr = \
        wavhelpers.load_stimuli(tone, testSR, testDuration, testFade, False)
    print('playing {}Hz tone for {} seconds'.format(tone, testDuration))
    playSound(monoChanStr)
