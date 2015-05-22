#!/usr/bin/env python3

from __future__ import print_function
import time
import os
import sys
import live555
import threading
import signal

# Shows how to use live555 module to pull frames from an RTSP/RTP
# source.  Run this (likely first customizing the URL below:

# Example: python3 example.py 10.17.4.118 1 10 out.264
if len(sys.argv) < 5:
    print('\nUsage: python3 {0} cameraIP channel seconds fileOut [pidfile]\n'.format(sys.argv[0]), file=sys.stderr)
    print('Example usage to record a playable stream indefinitely until a signal is received:\npython3 {0} cameraIP channel 0 - | ffmpeg -i - -vcodec copy -f mp4 video.mp4\n'.format(
        sys.argv[0]), file=sys.stderr)
    sys.exit(1)

cameraIP = sys.argv[1]
channel = sys.argv[2]

# NOTE: the username & password, and the URL path, will vary from one
# camera to another!  This URL path works with Hikvision:
url = 'rtsp://%s/Streaming/Channels/%s' % (cameraIP, channel)
useTCP = False

#
#
# No need to edit beyond this point (hopefully)
#
#

seconds = float(sys.argv[3])
fileOut = sys.argv[4]

pidfile = None
ourPid = os.getpid()
if len(sys.argv) == 6:
    pidfile = sys.argv[5]
    fPid = open(pidfile, 'w')
    fPid.write(str(ourPid))
    fPid.close()


stdout_mode = True if fileOut == '-' else False
capturing = False


def handler(signum, frame):
    print('Got signal {0}, shutting down'.format(signum), file=sys.stderr)
    shutdown()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

if not stdout_mode:
    fOut = open(fileOut, 'wb')


def oneFrame(codecName, bytes, sec, usec, durUSec):
    try:
        if stdout_mode:
            os.write(sys.stdout.fileno(), bytes)
        else:
            print('frame for %s: %d bytes' % (codecName, len(bytes)))
            fOut.write(bytes)
    except OSError:
        print('OSError, shutting down', file=sys.stderr)
        os.kill(ourPid, signal.SIGTERM)  # FIXME very hacky way to talk to the parent thread

# Starts pulling frames from the URL, with the provided callback:
live555.startRTSP(url, oneFrame, useTCP)

capturing = True

# Run Live555's event loop in a background thread:
t = threading.Thread(target=live555.runEventLoop, args=())
t.setDaemon(True)
t.start()


def shutdown():
    global capturing  # FIXME

    # Tell Live555's event loop to stop:
    if capturing:
        live555.stopEventLoop()
        capturing = False
    # Wait for the background thread to finish:
    t.join()
    if pidfile:
        os.unlink(pidfile)
    sys.exit(0)

endTime = time.time() + seconds
while seconds == 0.0 or time.time() < endTime:
    time.sleep(0.1)

shutdown()
