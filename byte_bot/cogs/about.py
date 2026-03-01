import discord
from discord.ext import commands

class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command()
    async def about(self, ctx):
        """Show a short description of Byte Bot and the Byte Club community."""

        embed = discord.Embed(
                title="Byte Bot",
                description="""
I help support the Byte Club server, a community built for learning, collaboration, and growth. Ask questions, share what you’re building, and help others where you can.
Keep things kind, respectful, and organized so the server stays useful for everyone.
""",
                color=discord.Color.pink()
            )

        embed.add_field(name="Creator", value="Tarabyte's Community", inline=False)

        await ctx.send(embed=embed)
        
async def setup(bot):
    await bot.add_cog(About(bot))