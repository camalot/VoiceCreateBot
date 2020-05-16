from discord.ext import commands
class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print('Logged in as')
        print(self.bot.user.name)
        print(self.bot.user.id)
        print('------')

    @commands.Cog.listener()
    async def on_disconnect(self):
        print('------')
        print('Bot Disconnected')
        print('------')

    @commands.Cog.listener()
    async def on_resumed(self):
        print('------')
        print('Bot Session Resumed')
        print('------')

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        print('------')
        print('On Error')
        print(event)
        traceback.print_exc()
        print('------')


def setup(bot):
    bot.add_cog(Events(bot))
