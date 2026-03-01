import discord
from discord.ext import commands

class RulesView(discord.ui.View):
    def __init__(self, channel_url: str):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Open Rules Channel",
                style=discord.ButtonStyle.link,
                url=channel_url,
            )
        )

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command()
    async def rules(self, ctx):
        """Summarize the server rules and link members to the rules channel."""

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return
        
        channel = discord.utils.get(ctx.guild.channels, name="rules")
        if channel is None:
            await ctx.send("The command expects a text channel named `rules` to exist in the server.")
            return

        await ctx.send(f"""
## Byte Club Rules 📝

1️⃣ Be kind and respectful.
                       
2️⃣ No discrimination, harassment, or hate.
                       
3️⃣ Keep everything safe for work.

4️⃣ No spam or repeated irrelevant messages.

5️⃣ Use channels for their intended purpose.

6️⃣ No unsolicited advertising or self-promo.

7️⃣ Respect boundaries and prefer public questions.

8️⃣ Follow Discord’s Terms of Service and Community Guidelines.

## See {channel.mention} for the full server rules.

""")

async def setup(bot):
    await bot.add_cog(Rules(bot))