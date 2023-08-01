from pymongo import MongoClient
from . import Migration
import inspect
import os

class Migration_00008(Migration):
    def __init__(self, connection):
        _method = inspect.stack()[0][3]
        super().__init__(connection)
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.log(f"{self._module}.{_method}", f"INITIALIZE MIGRATION 00008")
        pass

    def execute(self):
        _method = inspect.stack()[0][3]
        self.log(f"{self._module}.{_method}", f"EXECUTE MIGRATION 00008")
        # v8 migration start
        collections = self.connection.list_collection_names()


        self.log(f"{self._module}.{_method}", f"COMPLETE MIGRATION 00008")
