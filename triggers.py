#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from warnings import warn
from psychopy import parallel
import platform

PLATFORM = platform.platform()


if 'Linux' in PLATFORM:
    port = parallel.ParallelPort(address='/dev/parport0')  # on MEG stim PC
else:  # on Win this will work, on Mac we catch error below
    try:
        port = parallel.ParallelPort(address=0xDFF8)  # on MEG stim PC
    except TypeError:
        warn('Could not find parallel port. Is it connected?')
        port = None

# NB problems getting parallel port working under conda env
# from psychopy.parallel._inpout32 import PParallelInpOut32
# port = PParallelInpOut32(address=0xDFF8)  # on MEG stim PC
# parallel.setPortAddress(address='0xDFF8')
# port = parallel

# Figure out whether to flip pins or fake it
if port is not None:
    try:
        port.setData(128)
    except NotImplementedError:
        def setParallelData(code=1):
            if code > 0:
                # logging.exp('TRIG %d (Fake)' % code)
                print('TRIG %d (Fake)' % code)
                pass
    else:
        port.setData(0)
        setParallelData = port.setData
# If port hasn't been found, fake it
else:
    warn("Parallel port not found. Fake trigger will be used.")
    lastCode = 0
    def setParallelData(code=1):
        global lastCode
        if code > 0:
            print('TRIG %d (Fake): ON' % code)
            lastCode = code
        else:
            print('TRIG %d (Fake): OFF' % lastCode)
            lastCode = code

