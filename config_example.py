#!/usr/bin/env python2

import random

ftp_host = "example.com"
ftp_user = "yawkat"
ftp_password = "password"

ftp_directory = "screenshots"

image_format = "png"
filename_format = "%s.png"
copy_format = "http://example.com/%s"

def generate_name(used):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    res = ""
    for _ in range(4):
        res += random.choice(chars)
    return res
