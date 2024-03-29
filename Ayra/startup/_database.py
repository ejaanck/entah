# Ayra - UserBot
# Copyright (C) 2021-2022 senpai80
#
# This file is a part of < https://github.com/senpai80/Ayra/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/senpai80/Ayra/blob/main/LICENSE/>.

import ast
import os

from .. import run_as_module
from . import *

if run_as_module:
    from ..configs import Var


MongoClient = Database = None
if Var.MONGO_URI:
    try:
        from pymongo import MongoClient
    except ImportError:
        LOGS.info("Installing 'pymongo' for database.")
        os.system("pip3 install -q pymongo[srv]")
        from pymongo import MongoClient
else:
    try:
        from localdb import Database
    except ImportError:
        LOGS.info("Using local file as database.")
        os.system("pip3 install -q localdb.json")
        from localdb import Database

# --------------------------------------------------------------------------------------------- #


class _BaseDatabase:
    def __init__(self, *args, **kwargs):
        self._cache = {}

    def get_key(self, key):
        if key in self._cache:
            return self._cache[key]
        value = self._get_data(key)
        self._cache.update({key: value})
        return value

    def re_cache(self):
        self._cache.clear()
        for key in self.keys():
            self._cache.update({key: self.get_key(key)})

    def ping(self):
        return 1

    @property
    def usage(self):
        return 0

    def keys(self):
        return []

    def del_key(self, key):
        if key in self._cache:
            del self._cache[key]
        self.delete(key)
        return True

    def _get_data(self, key=None, data=None):
        if key:
            data = self.get(str(key))
        if data:
            try:
                data = ast.literal_eval(data)
            except BaseException:
                pass
        return data

    def set_key(self, key, value):
        value = self._get_data(data=value)
        self._cache[key] = value
        return self.set(str(key), str(value))

    def rename(self, key1, key2):
        _ = self.get_key(key1)
        if _:
            self.del_key(key1)
            self.set_key(key2, _)
            return 0
        return 1


class MongoDB(_BaseDatabase):
    def __init__(self, key, dbname=Var.DB_NAME):
        self.dB = MongoClient(key, serverSelectionTimeoutMS=5000)
        self.db = self.dB[dbname]
        super().__init__()

    def __repr__(self):
        return f"<Ayra.MonGoDB\n -total_keys: {len(self.keys())}\n>"

    @property
    def name(self):
        return "Mongo"

    @property
    def usage(self):
        return self.db.command("dbstats")["dataSize"]

    def ping(self):
        if self.dB.server_info():
            return True

    def keys(self):
        return self.db.list_collection_names()

    def set_key(self, key, value):
        if key in self.keys():
            self.db[key].replace_one({"_id": key}, {"value": str(value)})
        else:
            self.db[key].insert_one({"_id": key, "value": str(value)})
        self._cache.update({key: value})
        return True

    def delete(self, key):
        self.db.drop_collection(key)

    def get(self, key):
        if x := self.db[key].find_one({"_id": key}):
            return x["value"]

    def flushall(self):
        self.dB.drop_database(Var.DB_NAME)
        self._cache.clear()
        return True


# --------------------------------------------------------------------------------------------- #


class LocalDB(_BaseDatabase):
    def __init__(self):
        self.db = Database("ayra")
        super().__init__()

    def keys(self):
        return self._cache.keys()

    def __repr__(self):
        return f"<Ayra.LocalDB\n -total_keys: {len(self.keys())}\n>"


def AyraDB():
    _er = False
    from .. import HOSTED_ON

    try:
        if MongoClient:
            return MongoDB(Var.MONGO_URI)
    except BaseException as err:
        LOGS.exception(err)
        _er = True
    if not _er:
        LOGS.critical(
            "No DB requirement fullfilled!\nPlease install redis, mongo or sql dependencies...\nTill then using local file as database."
        )
    if HOSTED_ON == "okteto":
        return LocalDB()
    exit()


# --------------------------------------------------------------------------------------------- #
