from pymongo import MongoClient
from . import Migration
import inspect
import os
class Migration_00005(Migration):
    def __init__(self, connection):
        _method = inspect.stack()[0][3]
        super().__init__(connection)
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.log(f"{self._module}.{_method}", f"INITIALIZE MIGRATION 00005")
        pass
    def execute(self):
        _method = inspect.stack()[0][3]
        self.log(f"{self._module}.{_method}", f"EXECUTE MIGRATION 00005")
        # v5 migration start
        collections = self.connection.list_collection_names()
        if 'guild' in collections:
            self.connection['guild'].rename("create_channels")
        if 'guildCategorySettings' in collections:
            self.connection['guildCategorySettings'].rename("category_settings")
        if 'userSettings' in collections:
            self.connection['userSettings'].rename("user_settings")
        if 'textChannel' in collections:
            self.connection['textChannel'].rename("text_channels")
        if 'voiceChannel' in collections:
            self.connection['voiceChannel'].rename("voice_channels")
        # v5 migration end
        self.log(f"{self._module}.{_method}", f"COMPLETE MIGRATION 00005")
