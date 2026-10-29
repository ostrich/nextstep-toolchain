#!/usr/bin/env python3
"""Power off an owned disposable Previous guest through the native power dialog."""
import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from PIL import Image
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--lab',type=Path,required=True)
p.add_argument('--display',required=True)
p.add_argument('--timeout',type=int,default=120)
a=p.parse_args();lab=a.lab.resolve()
if not re.fullmatch(r':[0-9]+',a.display):p.error('Use a private X display such as :225')
pid=int((lab/'previous.pid').read_text())
process=Path('/proc')/str(pid)
command=(process/'cmdline').read_bytes().replace(b'\0',b' ').decode()
if str(lab) not in command or '/usr/bin/previous' not in command:p.error('PID does not identify this owned Previous lab')
env=os.environ.copy();env['DISPLAY']=a.display
def run(args):return subprocess.check_output(args,env=env,text=True)
focus=run(['xdotool','getwindowfocus','getwindowname']).strip()
if not any(x in focus for x in ['Previous','Mouse is locked']):p.error('Unexpected focused window: '+focus)
def screen():
    shot=lab/'power-confirmation.png'
    subprocess.run(['import','-window','root',str(shot)],env=env,check=True,stderr=subprocess.DEVNULL)
    text=subprocess.check_output(['tesseract',str(shot),'stdout','--psm','6'],stderr=subprocess.DEVNULL,text=True)
    # On the verified 1120x880 layout, the large flat background can make
    # whole-screen segmentation miss the centered native power dialog.
    with Image.open(shot) as im:
        if im.size == (1120, 880):
            crop=lab/'power-dialog-ocr.png'
            region=im.convert('L').crop((280,176,840,586))
            region.resize((1680,1230)).save(crop)
            text+='\n'+subprocess.check_output(['tesseract',str(crop),'stdout','--psm','6'],stderr=subprocess.DEVNULL,text=True)
    return text
def rom(text):
    return re.search(r'ROM\s+M[oa]nitor',text,re.I) is not None
text=screen()
if rom(text):
    # A visible ROM monitor is completed native halt, not an idle CPU sample.
    os.kill(pid,signal.SIGTERM)
else:
    run(['xdotool','key','F10'])
    deadline=time.monotonic()+15
    while True:
        if not process.exists():break
        try:
            text=screen()
        except subprocess.CalledProcessError:
            # Native power-off may exit Previous and its private X server
            # between the process check and screenshot capture.
            if not process.exists():break
            raise
        if 'really want' in text and re.search(r'Turn.*Off',text,re.I):
            run(['xdotool','key','Return']);break
        if rom(text):
            os.kill(pid,signal.SIGTERM);break
        if time.monotonic()>deadline:
            raise SystemExit('Unrecognized power confirmation; inspect guest before continuing')
        time.sleep(.5)
deadline=time.monotonic()+a.timeout
while time.monotonic()<deadline:
    if not process.exists():
        (lab/'native-poweroff.txt').write_text('Native power key requested; emulator exited naturally, or visible ROM halt confirmed.\n')
        print('Previous completed native halt and exited');break
    try:
        if rom(screen()):os.kill(pid,signal.SIGTERM)
    except (subprocess.CalledProcessError,ProcessLookupError):pass
    time.sleep(1)
else:raise SystemExit('Native power-off still pending; inspect guest before stopping emulator')
