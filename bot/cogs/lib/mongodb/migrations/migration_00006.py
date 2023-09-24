import inspect
import os

from bot.cogs.lib.mongodb.migration import Migration


class Migration_00006(Migration):
    def __init__(self, connection):
        _method = inspect.stack()[0][3]
        super().__init__(connection)
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.log(f"{self._module}.{_method}", f"INITIALIZE MIGRATION 00006")
        pass
    def execute(self):
        _method = inspect.stack()[0][3]
        self.log(f"{self._module}.{_method}", f"EXECUTE MIGRATION 00006")
        # v6 migration start
        collections = self.connection.list_collection_names()

        if "guild_settings" in collections:
            self.connection.guild_settings.update_many({}, { "$set": { "language": "en-us" } })

        self.log(f"{self._module}.{_method}", f"COMPLETE MIGRATION 00006")
