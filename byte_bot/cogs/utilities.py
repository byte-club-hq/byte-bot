from datetime import datetime, timezone
from logging import getLogger

import discord
from discord.ext import commands

from byte_bot.byte_bot import ByteBot

logger = getLogger(__name__)


class Utilities(commands.Cog):
    """
    A collection of utility commands for the bot.

    This Cog houses general-purpose commands such as `/about` that provides
    information about the bot, its status, uptime, and repository link.

    Args:
        bot (ByteBot): The bot instance that this cog is attached to.
    """

    def __init__(self, bot: ByteBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.debug("Utilities cog is ready and loaded.")

    @commands.hybrid_command(name="about", description="Learn more about the Byte Bot.")
    async def about(self, ctx: commands.Context) -> None:
        """
        Display information about the bot, including status, uptime, ping, and repository.

        This command generates a Discord embed containing:
        - Bot name
        - Repository link
        - Current version
        - Current status (online/idle/dnd)
        - Health indicator based on latency
        - Uptime since last restart
        - Number of uses the bot can see
        - Ping in millisecond

        The response is ephemeral to avoid cluttering channels.

        Args:
            ctx (commands.Context): The context in which the command was invoked,
            providing access to the channel, guild, author, and interaction.
        """
        bot = self.bot.user.name
        repo_link = "https://github.com/byte-club-hq/byte-bot"
        version = "1.0.0"
        ping = round(self.bot.latency * 1000)
        status = self.bot.status
        users = len(self.bot.users)

        # Calculate uptime
        now = datetime.now(timezone.utc)
        uptime_delta = now - self.bot.start_time
        days = uptime_delta.days
        hours = uptime_delta.seconds // 3600
        minutes = (uptime_delta.seconds % 3600) // 60
        formatted_uptime = f"{days}d {hours}h {minutes}m"

        # Determine healthy status based on latency (arbitrary thresholds)
        if status == discord.Status.online:
            if ping < 200:
                health = "🟢 Healthy"
            elif ping < 400:
                health = "🟡 Moderate"
            else:
                health = "🔴 Unhealthy"
        elif status == discord.Status.idle:
            health = "🟡 Moderate"
        elif status == discord.Status.dnd:
            health = "🟡 Moderate (Do Not Disturb)"
        else:  # offline or invisible
            health = "🔴 Unhealthy"

        embed = discord.Embed(
            title=f"🤖 About {bot}",
            description="A helpful Discord bot for the Byte Club community.",
            color=discord.Color.dark_blue(),
        )
        embed.add_field(name="📡 Ping", value=f"{ping}ms", inline=True)
        embed.add_field(name="🩺 Health", value=health, inline=True)
        embed.add_field(name="Status", value=str(status).title(), inline=True)
        embed.add_field(name="⏱️ Uptime", value=formatted_uptime, inline=True)
        embed.add_field(name="👥 Users", value=users, inline=True)
        embed.add_field(name="🔗 Repository", value=f"[GitHub Repository]({repo_link}) | 💻 v{version}", inline=False)
        embed.set_footer(text="Use / to explore commands • Made with ❤️ by Byte Club")

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="reloadcog")
    @commands.is_owner()  # this is used that only the bot owner can use this command
    async def reload_cog(self, ctx, cogs: str):
        """
        Reload one or more cogs without restarting the bot.
          Usage (comma-separated):
        1. +reloadcog leetcode,utilities
        2. /reloadcog leetcode,utilities
        """
        if not cogs:
            if ctx.interaction:
                await ctx.interaction.response.send_message("You must specify at least one cog.", ephemeral=True)
            else:
                await ctx.send("You must specify at least one cog.")
            return

        #  Split the input string by commas
        split_cogs = cogs.split(",")

        #  Create an empty list to hold cleaned cog names
        cog_list = []

        for c in split_cogs:
            clean_cog = c.strip()

            # Skip empty strings
            if clean_cog:
                # Add the cleaned cog name to the cog_list
                cog_list.append(clean_cog)

        results = []

        for cog in cog_list:
            extension_name = f"byte_bot.cogs.{cog}"
            try:
                await self.bot.reload_extension(extension_name)
                results.append(f"**{cog}** reloaded successfully.")
                logger.debug(f"Reloaded {cog}")
            except commands.ExtensionNotFound:
                logger.exception(f"Failed to reload the {cog} cog - ExtensionNotFound")
                results.append(f" **{cog}** not found.")
            except commands.ExtensionFailed:
                logger.exception(f"Failed to reload the {cog} cog due to ExtensionFailed")
                results.append(f" **{cog}** failed")
            except commands.ExtensionNotLoaded:
                logger.exception(f"Failed to reload the {cog} cog - ExtensionNotLoaded")
                results.append(f"**{cog}** is not loaded yet.")
            except Exception:
                # if there is unexpected error so this will run
                logger.exception(f"Unexpected error while reloading the {cog} cog")
                results.append(f"❌ **{cog}** unexpected error. Check logs.")

        # create an embed to display the results
        embed = discord.Embed(title="🔄 Cog Reload Report", color=discord.Color.blue())
        embed.description = "\n".join(results)

        if ctx.interaction:
            # Defer first for slash commands to avoid "no output"
            await ctx.interaction.response.defer(ephemeral=True)
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Prefix command
            await ctx.send(embed=embed)


# setup function to add in to the bot
async def setup(bot: ByteBot):
    await bot.add_cog(Utilities(bot))
