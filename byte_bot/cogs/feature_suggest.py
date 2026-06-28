import logging
from typing import Annotated

import discord
from discord.ext import commands
from discord import app_commands

from byte_bot.byte_bot import ByteBot
from byte_bot.services.feature_suggest_service import create_feature_suggestion

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ImageURL(commands.Converter):
    """Convert a command argument to an image URL, or reject it.

    Raising ``BadArgument`` on a non-URL token is deliberate. For an
    ``ImageURL | None`` parameter, discord.py's prefix parser catches the
    error, rewinds the string view (``view.undo()``), sets ``image`` to
    ``None``, and lets the rewound token fall through to the consume-rest
    ``summary`` parameter. So a URL is captured as the image, and any other
    word is handed back to the summary instead of being stolen.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if not argument.startswith(("http://", "https://")):
            raise commands.BadArgument("Not an image URL.")
        return argument


class FeatureSuggest(commands.Cog):
    """
    Cog for submitting feature suggestions to a forum channel.

    This cog provides a hybrid command `+suggestfeature` or `/suggestfeature` 
    that allows users to submit feature requests. It creates a thread in the
    designated forum channel and sends a confirmation message to the user.

    It also listens for:
    - Missing required arguments for commands and notifies users
    - Manually created threads in the forum channel and deletes them 
    to enforce structured submissions

    Attributes:
        feature_forum_channel_id (int): The ID of the forum channel where
        feature requests are submitted.
    """
    feature_forum_channel_id: int

    def __init__(self, bot: ByteBot):
        """
        Initialize the FeatureSuggest cog.

        Args:
            bot (ByteBot): The bot instance. Must have the attribute `feature_forum_channel_id` set.
        """
        self.bot = bot
        self.feature_forum_channel_id = self.bot.feature_forum_channel_id

    async def _reply(self, ctx: commands.Context, message: str):
        """
        Send a private reply to the user.

        Uses ephemeral messages for slash commands, DMs for text commands, 
        and falls back to public channel messages if DMs are blocked.

        Args:
            ctx (commands.Context): Command invocation context.
            message (str): The message to send to the user.

        Returns: None
        """
        if ctx.interaction:
            try:
                await ctx.interaction.response.send_message(message, ephemeral=True)
            except discord.InteractionResponded:
                await ctx.interaction.followup.send(message, ephemeral=True)
        else:
            try:
                await ctx.author.send(message)
            except discord.Forbidden:
                await ctx.send(message)

    @commands.hybrid_command(name="suggestfeature", description="Submit a feature suggestion.")
    @app_commands.describe(
        title='The title of your feature. Example (text command use quotes): "Dark Mode"',
        summary='A short summary of your feature. To attach a picture, also pick the optional "image" option.',
        image='Optional DIRECT image link (must end in .png/.jpg/.gif).'
    )
    async def suggest_feature(self, ctx: commands.Context, title: str, image: Annotated[str, ImageURL] | None, *, summary: str) -> None:
        """
        Submit a feature suggestion to the forum channel.

        This command can be used as either a text command (+suggestfeature) or 
        a slash command (/suggestfeature). It validated the title and summary, 
        creates a thread in the forum channel with an embed, and sends a 
        confirmation to the user.

        Args:
            ctx (commands.Context): The invocation context of the command. Can
                be a text message context or an interacction context.
            title (str): The title of the feature request. Max 256 characters.
                Multi-word titles in the text commands must be wrapped in quotes.
            summary (str): A brief description of the feature request. Max 1024 
                characters.
            image (Optional[ImageURL]): An optional direct image URL to attach to the embed.
                For prefixed commands, if no URL is provided, the first message attachment
                will be used if available.

        Returns: 
            None: Sends messages directly to Discord channels and/or users.

        Raises:
            discord.DiscordException: If sending the embed or creating the thread
                fails due to permissions or other Discord API issues.
        """
        if image is None and ctx.message.attachments:
            image = ctx.message.attachments[0].url

        try:
            suggestion = create_feature_suggestion(title, summary, image)
        except ValueError as error:
            await self._reply(ctx, str(error))
            return

        channel = self.bot.get_channel(self.feature_forum_channel_id)
        if channel is None:
            await self._reply(ctx, "❌ Could not find the forum channel.")
            return
        
        member = ctx.author
        avatar = getattr(member, "guild_avatar", None) or member.avatar
        icon_url = avatar.url if avatar else None     

        embed=discord.Embed(
            title="Feature Request",
            description="Allow community members to submit a feature request/suggestion.",
            color=discord.Color.brand_red(),
        )
        embed.add_field(name="Title", value=f"{suggestion.title}", inline=False)
        for i, chunk in enumerate(suggestion.summary_chunked):
            embed.add_field(name="Summary" if i == 0 else "​", value=chunk, inline=False)
        if suggestion.image:
            embed.set_image(url=suggestion.image)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=icon_url)

        # --- Send embed to forum thread ---
        try:
            if isinstance(channel, discord.ForumChannel):
                thread_with_message = await channel.create_thread(
                    name=suggestion.title,
                    embed=embed
                )
                thread = thread_with_message.thread
                logger.debug(f"Embed sent in new forum thread: {thread.name}")
            
                # --- Send confirmation to the user ---
                await self._reply(ctx, "✅ Your feature suggestion has been submitted!")
            else:
                logger.error(f"Channel {self.feature_forum_channel_id} is not a ForumChannel.")
                await self._reply(ctx, "❌ Feature suggestions channel is misconfigured.")
        except Exception:
            logger.exception("Failed to send embed:\n")
            await self._reply(ctx, "❌ Failed to submit your feature suggestion. Please check bot permissions.")
     
    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error):
        """
        Handle missing required arguments for commands.

        Listens for `commands.MissingRequiredArgument` errors and notifies 
        the user with instructions on how to use the command.

        Args:
            ctx (commands.Context): The context in which the command was invoked.
            error (Exception): the exception raised during command execution.

        Returns:
            None: Sends either an ephemeral message (slash command) or a DM
            (text command) to the user.
        """
        if ctx.command is None or ctx.command.name != "suggestfeature":
            return

        if isinstance(error, commands.MissingRequiredArgument):
            message = (
                "❌ You must provide both a **title** and a **summary**.\n\n"
                    "**How to use:**\n"
                    'Text command: +suggestfeature "Dark Mode" Add dark theme for users.\n'
                    'Slash command: /suggestfeature title:"Dark Mode" summary:"Add dark theme for users."\n\n'
                    "Make sure to put quotes around multi-word titles for text commands!"
            )
            await self._reply(ctx, message)
        elif isinstance(error, commands.BadArgument):
            await self._reply(
                ctx,
                "❌ The **image** option must be a direct image link starting with http:// or https://.",
            )

async def setup(bot: ByteBot):
    await bot.add_cog(FeatureSuggest(bot))
