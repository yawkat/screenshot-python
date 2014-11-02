#!/usr/bin/env python2

import os
import sys
import config
import redis

directory = sys.argv[1]

db = redis.StrictRedis(host=config.redis_host, port=config.redis_port, db=config.redis_db)

for f in os.listdir(directory):
    print("Copying %s..." % f)
    path = os.path.join(directory, f)
    ext_index = f.find(".")
    item_id = f[:ext_index]
    ext = f[ext_index + 1:]
    stat = os.stat(path)
    data = {
        "type": "image",
        "image_format": ext,
        "time": stat.st_mtime,
    }
    with open(path) as fo:
        data["image_blob"] = fo.read()
    db.hmset(item_id, data)
