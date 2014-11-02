#!/usr/bin/env python3

import os

key = os.urandom(16)

with open("secret", "w") as f:
    f.buffer.write(key)
