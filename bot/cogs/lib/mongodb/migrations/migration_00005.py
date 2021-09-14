from pymongo import MongoClient
from . import Migration
class Migration_00005(Migration):
    def __init__(self, connection):
        self.connection = connection
        self.log("Migration_00005.__init__", f"INITIALIZE MIGRATION 00005")
        pass
    def execute(self):
        self.log("Migration_00005.execute", f"EXECUTE MIGRATION 00005")
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
        self.log("Migration_00005.execute", f"COMPLETE MIGRATION 00005")
