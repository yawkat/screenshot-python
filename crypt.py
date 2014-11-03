#!/usr/bin/env python2

import os
import io
from Crypto.Cipher import AES
import hashlib

with open(os.path.dirname(__file__) + "/secret") as f:
    key = f.read(16)

aes_chunk_size = 16 * 1024

def _map_return(func):
    def dele(from_stream, **kwargs):
        stream = io.BytesIO()
        func(from_stream, stream, **kwargs)
        return stream.getvalue()
    return dele

def _map_pass(func):
    def dele(string, *args, **kwargs):
        stream = io.BytesIO(string)
        return func(stream, *args, **kwargs)
    return dele

def decrypt_stream_to_stream(from_stream, to_stream, limit=-1):
    read = 0
    while True:
        read += 16
        iv = from_stream.read(16)
        aes = AES.new(key, AES.MODE_CBC, iv)
        chunk_size = aes_chunk_size
        read += chunk_size
        if limit != -1 and read > limit:
            chunk_size -= read - limit
            read = limit
        chunk = from_stream.read(chunk_size)
        decrypted = aes.decrypt(chunk)
        to_stream.write(decrypted)
        if len(chunk) < aes_chunk_size or (limit >= 0 and read >= limit):
            break

decrypt_string_to_stream = _map_pass(decrypt_stream_to_stream)
decrypt_stream_to_string = _map_return(decrypt_stream_to_stream)
decrypt_string_to_string = _map_return(decrypt_string_to_stream)

def encrypt_stream_to_stream(from_stream, to_stream):
    while True:
        chunk = from_stream.read(aes_chunk_size)
        if len(chunk) == 0:
            break
        pad = 16 - (len(chunk) % 16)
        if pad != 16:
            chunk += "\x00" * pad
        print("Chunk write %s %s" % (len(chunk), hashlib.md5(chunk).hexdigest()))
        iv = os.urandom(16)
        to_stream.write(iv)
        aes = AES.new(key, AES.MODE_CBC, iv)
        to_stream.write(aes.encrypt(chunk))

encrypt_string_to_stream = _map_pass(encrypt_stream_to_stream)
encrypt_stream_to_string = _map_return(encrypt_stream_to_stream)
encrypt_string_to_string = _map_return(encrypt_string_to_stream)
