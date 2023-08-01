from pymongo import MongoClient
import traceback
import json
from .database import Database
import datetime
import discord
import typing

class ExporterMongoDatabase(Database):

    def __init__(self):
        super().__init__()
        pass

    def get_guilds(self):
        """Get all guilds"""
        try:
            if self.connection is None:
                self.open()
            return self.connection.guilds.find()
        except Exception as e:
            print(e)
            traceback.print_exc()
            # self.log.error(traceback.format_exc())
            return None
