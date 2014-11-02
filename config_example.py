#!/usr/bin/env python2

import random

def generate_name():
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    res = ""
    for _ in range(4):
        res += random.choice(chars)
    return res

image_format = "png"
url = "http://localhost:8888"
bind_address = "0.0.0.0"
bind_port = 8888
redis_host = "localhost"
redis_port = 6379
redis_db = 0

aes_chunk_size = 16 * 1024
