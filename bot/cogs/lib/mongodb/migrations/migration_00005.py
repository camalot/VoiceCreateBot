from pymongo import MongoClient

class Migration_00005:
    def __init__(self, connection):
        self.connection = connection
        pass
    def execute(self):
        print(f"EXECUTE MIGRATION 00005")
        # v5 migration start
        # if self.connection['guild']:
        #     self.connection['guild'].rename("create_channels")
        # if self.connection['guildCategorySettings']:
        #     self.connection['guildCategorySettings'].rename("category_settings")
        # if self.connection['userSettings']:
        #     self.connection['userSettings'].rename("user_settings")
        # if self.connection['textChannel']:
        #     self.connection['textChannel'].rename("text_channels")
        # if self.connection['voiceChannel']:
        #     self.connection['voiceChannel'].rename("voice_channels")
        # v5 migration end