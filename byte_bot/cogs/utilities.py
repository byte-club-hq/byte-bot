"""Utilities cog for byte-bot.

This cog contains general utility commands for the bot, including the reloadcog command
for hot-reloading cogs during development.
"""

import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Utilities(commands.Cog):
    """General utility commands for the bot."""

    def __init__(self, bot: commands.Bot):
        """Initialize the Utilities cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.hybrid_command(
        name="reloadcog",
        description="Reload one or more cogs without restarting the bot.",
    )
    @commands.is_owner()
    async def reloadcog(
        self, ctx: commands.Context, *, cog_names: str
    ) -> None:
        """Reload one or more cogs hot without restarting the bot.

        This command is useful during development to test changes to cogs
        without having to restart the entire bot and reconnect to Discord.

        Args:
            ctx: The command context.
            cog_names: Space-separated list of cog names to reload.
                      Cog names should be in the format 'cogs.cog_name'.

        Examples:
            +reloadcog cogs.utilities
            +reloadcog cogs.utilities cogs.fun
        """
        # Split the input into individual cog names
        cogs_to_reload = cog_names.split()

        if not cogs_to_reload:
            await ctx.send(
                "❌ Please provide at least one cog name to reload.\n"
                "Usage: `+reloadcog cogs.cog_name` or `+reloadcog cogs.cog1 cogs.cog2`"
            )
            return

        results = []
        success_count = 0
        fail_count = 0

        for cog_name in cogs_to_reload:
            cog_name = cog_name.strip()

            try:
                # Attempt to reload the extension
                await self.bot.reload_extension(cog_name)
                results.append(f"✅ **{cog_name}**: Reloaded successfully")
                success_count += 1
                log.info(f"Reloaded cog: {cog_name}")

            except commands.ExtensionNotFound:
                results.append(
                    f"❌ **{cog_name}**: Cog not found. "
                    f"Make sure the cog exists in the cogs directory."
                )
                fail_count += 1
                log.warning(f"Attempted to reload non-existent cog: {cog_name}")

            except commands.ExtensionNotLoaded:
                # Try to load it if it wasn't loaded
                try:
                    await self.bot.load_extension(cog_name)
                    results.append(
                        f"⚠️ **{cog_name}**: Was not loaded, now loaded successfully"
                    )
                    success_count += 1
                    log.info(f"Loaded cog that was not previously loaded: {cog_name}")
                except Exception as load_error:
                    results.append(
                        f"❌ **{cog_name}**: Failed to load - {str(load_error)}"
                    )
                    fail_count += 1
                    log.error(f"Failed to load cog {cog_name}: {load_error}")

            except commands.ExtensionFailed as e:
                results.append(
                    f"❌ **{cog_name}**: Failed to reload - {str(e.original)}"
                )
                fail_count += 1
                log.error(f"Failed to reload cog {cog_name}: {e}")

            except Exception as e:
                results.append(f"❌ **{cog_name}**: Unexpected error - {str(e)}")
                fail_count += 1
                log.error(f"Unexpected error reloading cog {cog_name}: {e}")

        # Create the embed response
        embed = discord.Embed(
            title="🔄 Cog Reload Results",
            color=discord.Color.green() if fail_count == 0 else discord.Color.orange(),
        )

        # Add summary field
        embed.add_field(
            name="Summary",
            value=f"✅ Success: {success_count} | ❌ Failed: {fail_count}",
            inline=False,
        )

        # Add detailed results
        embed.add_field(
            name="Details",
            value="\n".join(results) if results else "No cogs processed",
            inline=False,
        )

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Set up the Utilities cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Utilities(bot))
    log.info("Utilities cog loaded")
