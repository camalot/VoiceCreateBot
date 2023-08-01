from pymongo import MongoClient
import traceback
import json
from .. import utils
import os

class Database():

    def __init__(self):
        self.client = None
        self.connection = None
        self.db_url = utils.dict_get(os.environ, 'VCB_MONGODB_URL', default_value='')
        self.db_name = utils.dict_get(os.environ, 'VCB_MONGODB_DBNAME', default_value='voicecreate_v2')

    def open(self):
        if not self.db_url:
            raise ValueError("VCB_MONGODB_URL is not set")
        self.client = MongoClient(self.db_url)
        self.connection = self.client[self.db_name]
    def close(self):
        try:
            if self.client is not None and self.connection is not None:
                self.client.close()
                self.client = None
                self.connection = None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    
