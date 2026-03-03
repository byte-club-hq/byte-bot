import discord
from discord.ext import commands


class Utilities(commands.Cog):
    """Utility commands for the bot, including hot reload for cogs."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="reloadcog")
    @commands.is_owner()  # this is used that only the bot owner can use this command
    async def reloadcog(self, ctx, cogs: str):
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
            except commands.ExtensionNotFound:
                logger.exception(
                    f"Failed to reload the {cog} cog - ExtensionNotFound"
                )
                results.append(f" **{cog}** not found.")
            except commands.ExtensionFailed:
                logger.exception(
                    f"Failed to reload the {cog} cog due to ExtensionFailed"
                )
                results.append(f" **{cog}** failed")
            except commands.ExtensionNotLoaded:
                logger.exception(
                    f"Failed to reload the {cog} cog - ExtensionNotLoaded"
                )
                results.append(f"**{cog}** is not loaded yet.")
            except Exception:
                #if there is unexpected error so this will run 
                logger.exception(
                    f"Unexpected error while reloading the {cog} cog"
                )
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
async def setup(bot):
    await bot.add_cog(Utilities(bot))
