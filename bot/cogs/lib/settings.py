import sys
import os
import traceback
import glob
import typing
from . import utils
import json

class Settings:
    APP_VERSION = "1.0.0-snapshot"

    def __init__(self):
        try:
            with open('app.manifest') as json_file:
                self.__dict__.update(json.load(json_file))
        except Exception as e:
            print(e, file=sys.stderr)
        self.db_path = utils.dict_get(os.environ, 'VCB_DB_PATH', default_value = 'voice.db')
        self.admin_roles = utils.dict_get(os.environ, 'ADMIN_ROLES', default_value = 'Admin').split(',')
        self.admin_users = utils.dict_get(os.environ, 'ADMIN_USERS', default_value = 'Admin').split(' ')
        self.default_role = utils.dict_get(os.environ, 'DEFAULT_ROLE', default_value= '@everyone')
        self.bot_owner = utils.dict_get(os.environ, 'BOT_OWNER', default_value= '262031734260891648')
