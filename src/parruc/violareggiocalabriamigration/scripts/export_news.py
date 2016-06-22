# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime

import requests

from bs4 import BeautifulSoup
from plone.i18n.normalizer import idnormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unibo.violareggiocalabriamigration.export")

usage = "usage: %prog [options]"
parser = argparse.ArgumentParser(usage=usage, description=__doc__)
parser.add_argument(
    "-p", "--path", type=str, dest="export_path", default="exported",
    help="Results export folder. Default is 'exported'")
parser.add_argument(
    "-l", "--limit", type=int, dest="limit", default=0,
    help="Limit the number of pages to import (for debugging purpose)")
parser.add_argument(
    "-o", "--offset", type=int, dest="offset", default=0,
    help="Skips a certain number of pages (for debugging purpose)")
parser.add_argument(
    "-f", "--force",
    action="store_true", dest="force", default=False,
    help="Dont trust current structure, and overwrite it (slower)")


reject_links = ["#"]

VISITED_PAGES = []
TAKEN_PATHS = []
REDIRECTS = {}
BASE_URL = "http://www.violareggiocalabria.it"
COUNTER = 0
normalize = idnormalizer.normalize


def get_absolute_link(link):
    if link == "#":
        return ""
    if link.startswith("/"):
        link = BASE_URL + link
    if link.startswith("www.violareggiocalabria.it"):
        link = link.replace("www.violareggiocalabria.it", BASE_URL)
    return link


def save_json(export_path, data):
    global COUNTER
    if not data:
        return
    data["count"] = COUNTER
    file_name = normalize(data["title"].strip()) + ".json"
    path = os.sep.join((export_path, file_name))
    with open(path, 'w') as f:
        json.dump(data, f)
    COUNTER += 1


def get_url_checking(url):
    if not url:
        logger.warning("Found an empty link to '%s'", url)
        return None
    if url in VISITED_PAGES:
        logger.info("Link '%s' already visited", url)
        return None
    try:
        req = requests.get(url)
        req.raise_for_status()
    except:
        logger.warning("Found a broken link to '%s'", url)
        return None
    if req.url in VISITED_PAGES:
        logger.warning("Link redirected to already visited page '%s'", req.url)
        return None
    if not req.url.startswith(BASE_URL):
        logger.info("Link '%s' points outside", req.url)
        return None
    VISITED_PAGES.append(req.url)
    return req


def prepare_dict(url):
    req = get_url_checking(url)
    if not req:
        return
    parser = BeautifulSoup(req.content, 'html.parser')
    article = parser.select("div.item-page")[0]
    images = []
    for image in article.select("img"):
        src = ""
        alt = ""
        if image and "alt" in image.attrs:
            alt = image.get("alt")
        if image and "src" in image.attrs:
            src = get_absolute_link(image.get("src"))
            images.append({"alt": alt, "src": src})
    text = ""
    for paragraph in article.select("p"):
        paragraph_text = paragraph.get_text().strip()
        if paragraph_text:
            text += "<p>" + paragraph_text + "</p>"
    return {"images": images, "text": text, "url": req.url}


def export_news(offset, limit, force, export_path):
    data = {"limit": "0"}
    req = requests.post("http://www.violareggiocalabria.it/news/news", data)
    parser = BeautifulSoup(req.content, 'html.parser')
    if not os.path.exists(export_path):
        os.makedirs(export_path)
    rows = parser.select("table.category tbody tr")
    for row in rows:
        columns = row.select("td")
        link = columns[0].select("a")[0]
        url = get_absolute_link(link["href"])
        res = prepare_dict(url)
        if not res:
            return
        title = link.text.strip()
        date_str = columns[1].text.strip()
        iso_date = datetime.strptime(date_str, "%d-%m-%y").isoformat()
        res["title"] = title
        res["id"] = normalize(title, max_length=200)
        res["date"] = iso_date
        res["hits"] = columns[2].text.strip()
        save_json(export_path, res)


def main(*args, **kwargs):
    # Older plone versions dont add automatic -c script parameters
    # So I'll stripe the parameters until I reach the script
    if "-c" in sys.argv:
        cmd_args = sys.argv[3:]
    else:
        cmd_args = sys.argv[1:]
    options = vars(parser.parse_args(cmd_args))
    original_path = options["export_path"]
    if "force" in options and options["force"]:
        shutil.rmtree(original_path)
    export_news(**options)
