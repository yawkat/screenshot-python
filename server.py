#!/usr/bin/env python2

import os
import BaseHTTPServer
import redis
import argparse
import re
import config
import crypt
import collections
import rencode
import jinja2
import time
import datetime
import cStringIO
import Image
import argparse
import markdown

parser = argparse.ArgumentParser()
parser.add_argument("--no-cache", action="store_false", dest="cache")

options = parser.parse_args()

db = redis.StrictRedis(host=config.redis_host, port=config.redis_port, db=config.redis_db)

def get_db_entry(item_id):
    entry = db.hgetall(item_id)
    if len(entry) == 0:
        return None
    else:
        return dict(entry)

class TemplateEngine():
    def __init__(self, prefix, suffix):
        self.prefix = prefix
        self.suffix = suffix
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(prefix), autoescape=True)
        self.template_cache = {}

    def compile(self, name):
        print("Loading template '%s'" % name)
        return self.env.get_template(name + self.suffix)

    def render(self, name, args):
        args["site_url"] = config.url
        if options.cache:
            try:
                template = self.template_cache[name]
            except KeyError:
                template = self.compile(name)
                self.template_cache[name] = template
        else:
            template = self.compile(name)
        return template.render(**args)

templates = TemplateEngine("template/", ".html")

def path_dict():
    return collections.defaultdict(path_dict)

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def _mime(self, mime):
        self.send_header("Content-Type", mime)

    def do_GET(self):
        for special, handler in special_urls.items():
            match = special.match(self.path)
            if match:
                handled = handler(self, match)
                if handled or handled is None: # none for void
                    return
        item_id = self.path[1:]
        entry = get_db_entry(item_id)
        if entry is None:
            self.e404()
        else:
            if entry["type"] == "url":
                self.send_response(301)
                self.send_header("Location", entry["url"])
            else:
                self.send_response(200)
                self._mime("text/html; charset=utf-8")
            self.end_headers()
            entry["id"] = item_id
            entry["time_stamp"] = datetime.datetime.utcfromtimestamp(float(entry["time"])).strftime("%Y-%m-%d %H-%M-%S")
            html = templates.render(entry["type"], entry)
            self.wfile.write(html)

    def do_POST(self):
        data_str = crypt.decrypt_stream_to_string(self.rfile, limit=int(self.headers["Content-Length"])).strip()
        data = dict(rencode.loads(data_str))
        data["time"] = time.time()
        while True:
            item_id = config.generate_name()
            if db.hlen(item_id) == 0:
                # todo: stop ignoring this race condition
                db.hmset(item_id, data)
                break
        self.send_response(200)
        self.end_headers()
        response = {
            "item": item_id,
            "url": config.url + "/" + item_id,
        }
        crypt.encrypt_string_to_stream(rencode.dumps(response), self.wfile)

    def _dump_image(self, match, min_dimensions=(-1, -1)):
        item_id = match.group(1)
        entry = get_db_entry(item_id)
        if entry is None:
            return False
        self.send_response(200)
        self._mime("image/" + entry["image_format"])
        self.end_headers()
        blob = entry["image_blob"]
        if min_dimensions != (-1, -1):
            image = Image.open(cStringIO.StringIO(blob))
            dimensions = [max(min_dimensions[i], image.size[i]) for i in range(2)]
            if dimensions != image.size:
                new_image = Image.new("RGB", dimensions, (255, 255, 255))
                new_image.paste(image, (0, 0))
                stream = cStringIO.StringIO()
                new_image.save(stream, entry["image_format"])
                blob = stream.getvalue()
        self.wfile.write(blob)

    def _dump_image_twitter(self, match):
        self._dump_image(match, (280, 150))

    def _dump_svg(self, match):
        item_id = match.group(1)
        entry = get_db_entry(item_id)
        if entry is None:
            return False
        self.send_response(200)
        self._mime("image/svg+xml")
        self.end_headers()
        self.wfile.write(entry["svg_blob"])

    def _dump_text(self, match):
        item_id = match.group(1)
        entry = get_db_entry(item_id)
        if entry is None:
            return False
        self.send_response(200)
        self._mime("text/plain")
        self.end_headers()
        blob = entry["code_text"]
        self.wfile.write(blob)

    def _dump_video(self, match):
        item_id = match.group(1)
        entry = get_db_entry(item_id)
        if entry is None:
            return False
        self.send_response(200)
        self._mime("video/webm ")
        self.end_headers()
        blob = entry["video_blob"]
        self.wfile.write(blob)

    def _render_markdown(self, match):
        item_id = match.group(1)
        entry = get_db_entry(item_id)
        if entry is None:
            return False
        self.send_response(200)
        self._mime("text/html; charset=utf-8")
        self.end_headers()
        entry["id"] = item_id
        entry["time_stamp"] = datetime.datetime.utcfromtimestamp(float(entry["time"])).strftime("%Y-%m-%d %H-%M-%S")
        entry["code_render"] = markdown.markdown(entry["code_text"])
        html = templates.render("markdown_render", entry)
        self.wfile.write(html)

    def e404(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write(templates.render("404", {}))

special_urls = {
    re.compile(r"/([^/]*)\.twitter\.(png|je?pg|gif|bmp)"): Handler._dump_image_twitter,
    re.compile(r"/([^/]*)\.(png|je?pg|gif|bmp)"): Handler._dump_image,
    re.compile(r"/([^/]*)\.svg"): Handler._dump_svg,
    re.compile(r"/([^/]*)\.txt"): Handler._dump_text,
    re.compile(r"/([^/]*)\.webm"): Handler._dump_video,
    re.compile(r"/([^/]*)\.rmd"): Handler._render_markdown,
}

server = BaseHTTPServer.HTTPServer((config.bind_address, config.bind_port), Handler)
server.serve_forever()
