#!/usr/bin/env python2

import os
import sys
import pyscreenshot
import Tkinter as tk
import Image
from PIL import ImageTk
import io
import pyperclip
import urllib
import urllib2
import crypt
import rencode
import subprocess
import urlparse
import tempfile
import time
import signal

import config

def upload_image(image):
    f = io.BytesIO()
    image.save(f, config.image_format)
    obj = {
        "type": "image",
        "image_format": config.image_format,
        "image_blob": f.getvalue(),
    }
    upload(obj, "Screenshot uploaded: %s")

def upload_svg(svg):
    obj = {
        "type": "svg",
        "svg_blob": svg,
    }
    upload(obj, "SVG uploaded: %s")

def upload_code(text):
    obj = {
        "type": "code",
        "code_text": text,
    }
    upload(obj, "Paste uploaded: %s")

def upload_url(url):
    obj = {
        "type": "url",
        "url": url
    }
    upload(obj, "URL shortened: %s")

def upload_video(data):
    obj = {
        "type": "video",
        "video_blob": data
    }
    upload(obj, "Video uploaded: %s")

def upload(obj, notification_format):
    data = crypt.encrypt_string_to_string(rencode.dumps(obj))
    request = urllib2.urlopen(config.url, data=data)
    response_string = crypt.decrypt_stream_to_string(request)
    response = rencode.loads(response_string)
    url = response["url"]
    pyperclip.copy(url)
    subprocess.Popen(["notify-send", "--expire-time=2000", notification_format % url])

def take_screen():
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

    global area, image_arr, items
    area = 0, 0, 0, 0
    items = []
    image_arr = []

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
        print("Shot", area)
        frame.master.destroy()
        box = (
            min(area[0], area[0] + area[2]),
            min(area[1], area[1] + area[3]),
            max(area[0], area[0] + area[2]),
            max(area[1], area[1] + area[3]),
        )
        selected = img.crop(box)
        upload_image(selected)

    frame.bind("<Escape>", sys.exit)
    canvas.bind("<Button-1>", down)
    canvas.bind("<B1-Motion>", move)
    canvas.bind("<ButtonRelease-1>", up)

    frame.pack()

    # force focus on the frame
    frame.after(0, lambda: frame.master.focus_force())
    frame.focus_set()

    frame.mainloop()

    print("Done")

def take_clipboard():
    import gtk
    clipboard = gtk.Clipboard()

    pixbuf = clipboard.wait_for_image()
    if pixbuf is not None:
        pixels = pixbuf.get_pixels()
        if pixbuf.get_has_alpha():
            colorspace = "RGBA"
        else:
            colorspace = "RGB"
        img = Image.fromstring(colorspace, (pixbuf.get_width(), pixbuf.get_height()), pixels)
        upload_image(img)
        return
    else:
        print("Not an image")

    text = clipboard.wait_for_text()
    if text is not None:
        print("Text: %s" % text)
        try:
            img = Image.open(text)
        except:
            print("Failed to use image file source")
        else:
            upload_image(img)
            return
        try:
            f = None
            f = open(text)
            start = f.read(200)
            print(start)
            start.index("<svg")
        except:
            print("Failed to use svg file source")
            if f is not None:
                f.close()
        else:
            upload_svg(start + f.read())
            f.close()
            return

        parsed_url = urlparse.urlparse(text)
        if parsed_url.scheme in ("http", "https"):
            upload_url(text)
        else:
            upload_code(text)

def capture_or_end_screen():
    pid_file = "screencast.pid"
    if os.path.isfile(pid_file):
        with open(pid_file) as f:
            pid = int(f.read())
        try:
            os.kill(pid, signal.SIGINT)
            return
        except OSError:
            pass
    
    record_screen(pid_file)

def record_screen(pid_file):
    pid = os.getpid()
    with open(pid_file, "w") as f:
        f.write(str(pid))

    sc_avi = "screencast.avi"
    proc = subprocess.Popen([
        "avconv", "-y", "-f", "x11grab", "-r", "10", 
        "-s", "1366x768", "-i", ":0.0+0,0", "-vcodec", "libx264", 
        "-pre", "lossless_ultrafast",
        sc_avi
    ])

    def stop(num, frm):
        print("Received SIGINT, saving...")
        proc.terminate()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.remove(pid_file)
    signal.signal(signal.SIGINT, stop)

    proc.wait()

    sc_webm = "screencast.webm"
    proc = subprocess.Popen([
        "avconv", "-y", "-i", sc_avi, "-vcodec", "libvpx", 
        "-b:v", "1M", "-qmin", "20", "-qmax", "42", sc_webm
    ])
    proc.wait()
    os.remove(sc_avi)

    with open(sc_webm) as f:
        data = f.read()
    os.remove(sc_webm)
    upload_video(data)

if __name__ == '__main__':
    if len(sys.argv) <= 1 or sys.argv[1] == "screen":
        take_screen()
    elif sys.argv[1] == "clipboard":
        take_clipboard()
    elif sys.argv[1] == "screencast":
        capture_or_end_screen()
