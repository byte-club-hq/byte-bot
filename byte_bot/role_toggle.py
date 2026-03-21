import json
import logging
from pathlib import Path

import discord

log = logging.getLogger(__name__)

ROLE_NAME = "ByteClubHQ"
ROLE_TOGGLE_EMOJI = "\u2705"
ROLE_TOGGLE_TITLE = "ByteClubHQ Access"
ROLE_TOGGLE_STATE_FILE = Path(__file__).resolve().parents[1] / "role_toggle_state.json"
ROLE_TOGGLE_MESSAGE = (
    "Welcome to ByteClubHQ.\n\n"
    "Use the reaction below to toggle access to the community role.\n"
    f"{ROLE_TOGGLE_EMOJI} {ROLE_NAME}\n\n"
    "Add your reaction to join.\n"
    "Remove your reaction to leave."
)


class RoleReactionManager:
    """Manage ByteClubHQ role creation and reaction-based membership changes."""

    # Store bot references and restore the saved role-toggle message id.
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.channel_id = bot.config.ByteBotHQ_ROLE_CHANNEL_ID
        self.role_toggle_message_id = self._load_saved_message_id()

    async def setup(self, guild: discord.Guild) -> None:
        """Create the role if needed, then ensure the reaction panel exists."""
        await self._ensure_role(guild)

        if await self._toggle_message_exists():
            log.info(f"Using existing role toggle message {self.role_toggle_message_id}")
            return

        await self._send_role_toggle_message()

    # Give the role when a user adds the configured reaction.
    async def handle_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if self.bot.user is not None and payload.user_id == self.bot.user.id:
            return

        if not self._is_role_toggle_reaction(payload):
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        await self._toggle_role_for_member(guild, payload.user_id, should_have_role=True)

    # Remove the role when a user removes the configured reaction.
    async def handle_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if not self._is_role_toggle_reaction(payload):
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        await self._toggle_role_for_member(guild, payload.user_id, should_have_role=False)

    # Check whether this raw reaction event belongs to the toggle panel.
    def _is_role_toggle_reaction(self, payload: discord.RawReactionActionEvent) -> bool:
        if self.role_toggle_message_id is None:
            return False

        if payload.channel_id != self.channel_id:
            return False

        if payload.message_id != self.role_toggle_message_id:
            return False

        if payload.guild_id is None:
            return False

        return str(payload.emoji) == ROLE_TOGGLE_EMOJI

    # Create the community role if the guild does not already have it.
    async def _ensure_role(self, guild: discord.Guild) -> None:
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if role is not None:
            log.info(f"Role '{ROLE_NAME}' already exists")
            return
        await guild.create_role(
            name=ROLE_NAME,
            color=discord.Color.blue(),
            mentionable=True,
        )
        log.info(f"Created role '{ROLE_NAME}' in guild '{guild.name}'")

    # Get the configured channel from cache first, then fall back to the API.
    async def _get_role_toggle_channel(self) -> discord.abc.MessageableChannel | None:
        channel = self.bot.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except discord.HTTPException:
                log.exception(f"Role toggle channel {self.channel_id} could not be fetched")
                return None

        return channel

    # Post the embed users react to and save its message id for later reuse.
    async def _send_role_toggle_message(self) -> None:
        channel = await self._get_role_toggle_channel()
        if channel is None:
            log.error(f"Role toggle channel {self.channel_id} was not found")
            return

        embed = discord.Embed(
            title=ROLE_TOGGLE_TITLE,
            description=ROLE_TOGGLE_MESSAGE,
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Reaction role panel")

        message = await channel.send(embed=embed)
        await message.add_reaction(ROLE_TOGGLE_EMOJI)
        self.role_toggle_message_id = message.id
        self._save_message_id(message.id)
        log.info("Sent role toggle message")

    # Add or remove the role so the member matches the current reaction state.
    async def _toggle_role_for_member(self, guild: discord.Guild, user_id: int, should_have_role: bool) -> None:
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if role is None:
            log.warning(f"Role '{ROLE_NAME}' does not exist in guild '{guild.name}'")
            return

        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                log.warning(f"Could not fetch member {user_id} in guild '{guild.name}'")
                return

        has_role = role in member.roles
        if should_have_role and not has_role:
            await member.add_roles(role, reason="User reacted to role toggle message")
            log.info(f"Added role '{role.name}' to {member}")
            return

        if not should_have_role and has_role:
            await member.remove_roles(role, reason="User removed reaction from role toggle message")
            log.info(f"Removed role '{role.name}' from {member}")

    # Verify that the saved toggle message still exists in the target channel.
    async def _toggle_message_exists(self) -> bool:
        if self.role_toggle_message_id is None:
            return False

        channel = await self._get_role_toggle_channel()
        if channel is None or not isinstance(channel, discord.TextChannel):
            return False

        try:
            await channel.fetch_message(self.role_toggle_message_id)
        except discord.NotFound:
            log.warning(f"Saved role toggle message {self.role_toggle_message_id} no longer exists")
            self.role_toggle_message_id = None
            self._save_message_id(None)
            return False
        except discord.HTTPException:
            log.exception(f"Could not fetch saved role toggle message {self.role_toggle_message_id}")
            return False

        return True

    # Read the saved message id from disk so the panel can survive restarts.
    def _load_saved_message_id(self) -> int | None:
        if not ROLE_TOGGLE_STATE_FILE.exists():
            return None

        try:
            state = json.loads(ROLE_TOGGLE_STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.exception(f"Failed to read role toggle state from {ROLE_TOGGLE_STATE_FILE}")
            return None

        message_id = state.get("message_id")
        if isinstance(message_id, int):
            return message_id

        return None

    # Save the current toggle message id so it can be reused after a restart.
    def _save_message_id(self, message_id: int | None) -> None:
        try:
            ROLE_TOGGLE_STATE_FILE.write_text(
                json.dumps({"channel_id": self.channel_id, "message_id": message_id}, indent=2),
                encoding="utf-8",
            )
        except OSError:
            log.exception(f"Failed to write role toggle state to {ROLE_TOGGLE_STATE_FILE}")
