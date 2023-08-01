from pymongo import MongoClient
import traceback
import json

# from discord.ext.commands.converter import CategoryChannelConverter
from . import database
from .. import settings

class Database():

    def __init__(self):
        self.settings = settings.Settings()
        self.client = None
        self.connection = None

    def open(self):
        if not self.settings.db_url:
            raise ValueError("VCB_MONGODB_URL is not set")
        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client[self.settings.db_name]
    def close(self):
        try:
            if self.client is not None and self.connection is not None:
                self.client.close()
                self.client = None
                self.connection = None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
