#!/usr/bin/env python2

import os
import sys
import pyscreenshot
import Tkinter as tk
import Image
from PIL import ImageTk
import ftplib
import cStringIO
import pyperclip

import config

def upload(image):
    connection = ftplib.FTP(config.ftp_host)
    connection.login(config.ftp_user, config.ftp_password)
    existing = set(connection.cwd(config.ftp_directory))
    while True:
        gen = config.generate_name(existing)
        name = config.filename_format % gen
        print name
        if not name in existing:
            break
    f = cStringIO.StringIO()
    image.save(f, config.image_format)
    connection.storbinary("STOR " + name, cStringIO.StringIO(f.getvalue()))
    connection.quit()
    url = config.copy_format % gen
    pyperclip.copy(url)
    os.system("notify-send --expire-time=2000 \"Screenshot uploaded\" \"" + url + "\"")

### take screenshot

img = pyscreenshot.grab()
img_dark = img.point(lambda c: c * 0.5)
bbox = img.getbbox()

### display

frame = tk.Frame(width=bbox[2], height=bbox[3])
# xlib hacks to float above WM
frame.master.attributes("-type", "dock")
frame.master.attributes("-topmost", "true")

# convert to PhotoImage for tk
img_tk = ImageTk.PhotoImage(img)

canvas = tk.Canvas(frame, bg="#002b36", width=bbox[2], height=bbox[3])
canvas.pack()
canvas.place(x=-1, y=-1)

canvas.create_image((0, 0), image=img_tk, anchor=tk.NW)

area = 0, 0, 0, 0
items = []

def redraw():
    global image_arr, items
    for item in items:
        canvas.delete(item)
    items = []
    if area[2] is not 0 or area[3] is not 0:
        top_left = area[0:2]
        bottom_right = (area[0] + area[2], area[1] + area[3])
        top_left, bottom_right = (
            (min(top_left[0], bottom_right[0]), min(top_left[1], bottom_right[1])), 
            (max(top_left[0], bottom_right[0]), max(top_left[1], bottom_right[1]))
        )
        slice_boxes = (
            (0, 0, top_left[0], bbox[3]),
            (top_left[0], 0, bottom_right[0], top_left[1]),
            (bottom_right[0], 0, bbox[2], bbox[3]),
            (top_left[0], bottom_right[1], bottom_right[0], bbox[3]),
        )
    else:
        # just the full screen
        slice_boxes = (bbox,)

    image_arr = []
    for slice_box in slice_boxes:
        slice_image = ImageTk.PhotoImage(img_dark.crop(slice_box))
        image_arr.append(slice_image)
        item = canvas.create_image(slice_box[:2], image=slice_image, anchor=tk.NW)
        items.append(item)

redraw()

selecting = False

def down(evt):
    global selecting, area
    selecting = True
    area = (evt.x, evt.y, 0, 0)
def move(evt):
    global selecting, area
    if selecting:
        width = evt.x - area[0]
        height = evt.y - area[1]
        area = (area[0], area[1], width, height)
        redraw()
def up(evt):
    print "Shot", area
    frame.master.destroy()
    selected = img.crop((area[0], area[1], area[0] + area[2], area[1] + area[3]))
    upload(selected)

frame.bind("<Escape>", sys.exit)
canvas.bind("<Button-1>", down)
canvas.bind("<B1-Motion>", move)
canvas.bind("<ButtonRelease-1>", up)

frame.pack()

# force focus on the frame
frame.after(0, lambda: frame.master.focus_force())
frame.focus_set()

frame.mainloop()

print "Done"
