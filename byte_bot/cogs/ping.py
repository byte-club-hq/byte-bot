from discord.ext import commands

class Ping(commands.Cog):
    """Utility commands for bot health and quick diagnostics."""

    def __init__(self, bot):
        self.bot = bot
    
    # hybrid_command makes one command work as both slash and prefix command
    @commands.hybrid_command()
    async def ping(self, ctx):
        """Reply with the bot's current gateway latency in milliseconds."""

        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong 🏓 | {latency} ms")

async def setup(bot):
    await bot.add_cog(Ping(bot))