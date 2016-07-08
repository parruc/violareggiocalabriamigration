# -*- coding: utf-8 -*-
import json
import logging
import os.path
from datetime import datetime

import requests
from zope.interface import classProvides, implements

from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import resolvePackageReferenceOrFile

logger = logging.getLogger("unibo.violareggiocalabriamigration.import")
logging.basicConfig(level=logging.WARNING)


class Source(object):
    """Based on transmogrify.filesystem.source.FilesystemSource
    this section which can read files from the filesystem
    and set items'pipeline
    """

    implements(ISection)
    classProvides(ISectionBlueprint)

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.directory = resolvePackageReferenceOrFile(options['directory'])

    def __iter__(self):

        for item in self.previous:
            yield item

        if not os.path.exists(self.directory):
            raise ValueError("Directory %s does not exist" % self.directory)
        res = {}
        res['_type'] = u"Folder"
        res['_path'] = u"/notizie"
        res["title"] = u"Notizie"
        yield res

        for dir_path, dir_names, file_names in os.walk(self.directory):
            file_names.sort()
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                with open(file_path, 'rb') as input_file:
                    input_data = input_file.read()
                metadata = json.loads(input_data)
                res['_type'] = u"News Item"
                res['_path'] = u"/notizie/" + metadata["id"]
                res['subjects'] = metadata["category"]
                res['featured'] = metadata["featured"]
                res["title"] = unicode(metadata["title"])
                res["text"] = unicode(metadata["text"])
                res["pub_date"] = datetime.strptime(metadata["pub_date"],
                                                    '%Y-%m-%d %H:%M:%S')
                res["mod_date"] = datetime.strptime(metadata["mod_date"],
                                                    '%Y-%m-%d %H:%M:%S')
                for image in metadata["images"]:
                    data = None
                    url = image["src"]
                    try:
                        req = requests.get(url)
                        req.raise_for_status()
                    except:
                        logger.warning("Found a broken image in '%s'", url)
                        continue
                    data = req.content
                    filename = url.split("/")[-1]
                    res['image'] = {"data": data, "filename": filename}
                    break

                yield res
