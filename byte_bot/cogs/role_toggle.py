import logging

import discord
from discord.ext import commands
from discord import app_commands

from byte_bot.services.role_toggle_service import (
    DEFAULT_ROLE_NAME,
    DEFAULT_TOGGLE_EMOJI,
    DEFAULT_TOGGLE_TITLE,
    RoleToggleService,
)

log = logging.getLogger(__name__)


def _build_role_toggle_embed(*, title: str, role_name: str, emoji: str) -> discord.Embed:
    description = (
        f"Welcome to {role_name}.\n\n"
        "Use the reaction below to toggle access to the community role.\n"
        f"{emoji} {role_name}\n\n"
        "Add your reaction to join.\n"
        "Remove your reaction to leave."
    )
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    embed.set_footer(text="Reaction role panel")
    return embed


class RoleToggleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service = RoleToggleService(bot.database_service)
        self._setup_complete = False
        self._role_channel_id: int | None = None

    async def _reply(self, ctx: commands.Context, message: str) -> None:
        if ctx.interaction:
            try:
                await ctx.interaction.response.send_message(message, ephemeral=True)
            except discord.InteractionResponded:
                await ctx.interaction.followup.send(message, ephemeral=True)
        else:
            await ctx.send(message)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # on_ready can fire more than once (reconnects).
        if self._setup_complete:
            return
        self._setup_complete = True

        # One channel for all panels, configured via env.
        self._role_channel_id = getattr(self.bot.config, "ROLE_CHANNEL_ID", None)
        if not self._role_channel_id:
            log.info("ROLE_CHANNEL_ID not set; skipping role-toggle setup")
            return

        channel = await self._get_text_channel(self._role_channel_id)
        if channel is None:
            log.warning("ROLE_CHANNEL_ID %s is not a usable text channel; skipping role-toggle setup", self._role_channel_id)
            return

        await self._ensure_all_panels(channel.guild, channel)

    async def _ensure_all_panels(self, guild: discord.Guild, channel: discord.TextChannel) -> None:
        # Keep the default panel around.
        if self.service.get_panel(guild.id, role_name=DEFAULT_ROLE_NAME) is None:
            self.service.upsert_panel(
                guild_id=guild.id,
                role_name=DEFAULT_ROLE_NAME,
                emoji=DEFAULT_TOGGLE_EMOJI,
                title=DEFAULT_TOGGLE_TITLE,
            )

        for panel in self.service.list_panels(guild.id):
            try:
                await self._ensure_panel(guild, channel, panel)
            except discord.Forbidden:
                log.error("Missing permissions to set up role-toggle panel in guild '%s'", guild.name)
            except Exception:
                log.exception("Failed to set up role-toggle panel in guild '%s'", guild.name)

    async def _get_text_channel(self, channel_id: int) -> discord.TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return None

        if isinstance(channel, discord.TextChannel):
            return channel
        return None

    async def _ensure_panel(self, guild: discord.Guild, channel: discord.TextChannel, panel) -> None:
        role = await self.service.ensure_role(guild, panel.role_name)
        embed = _build_role_toggle_embed(title=panel.title, role_name=role.name, emoji=panel.emoji)

        message = None
        if panel.message_id:
            try:
                message = await channel.fetch_message(panel.message_id)
            except discord.NotFound:
                # Panel message was deleted; we'll recreate it.
                self.service.set_message_id(guild_id=panel.guild_id, role_name=panel.role_name, message_id=None)
                message = None
            except discord.Forbidden:
                # Can't read message history; don't risk posting duplicates.
                log.error("Forbidden fetching role-toggle message %s in #%s", panel.message_id, channel.name)
                return
            except discord.HTTPException:
                log.exception("HTTP error fetching role-toggle message %s in #%s", panel.message_id, channel.name)
                return

        if message is None:
            message = await channel.send(embed=embed)
            self.service.set_message_id(guild_id=panel.guild_id, role_name=panel.role_name, message_id=message.id)

        else:
            await message.edit(embed=embed)

        try:
            await message.add_reaction(panel.emoji)
        except discord.HTTPException:
            log.warning("Could not add reaction %s to role-toggle message %s", panel.emoji, message.id)

    @commands.hybrid_command(name="roletoggle_status", description="Show the role-toggle configuration for this server.")
    async def role_toggle_status(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await self._reply(ctx, "This command can only be used in a server.")
            return

        if not self._role_channel_id:
            await self._reply(ctx, "ROLE_CHANNEL_ID is not set. Role toggles are disabled.")
            return

        panels = self.service.list_panels(ctx.guild.id)
        default_panel = self.service.get_panel(ctx.guild.id, role_name=DEFAULT_ROLE_NAME)
        default_name = default_panel.role_name if default_panel else DEFAULT_ROLE_NAME
        await self._reply(
            ctx,
            f"Role-toggle channel: <#{self._role_channel_id}>. Panels: {len(panels)}. Default: `{default_name}`.",
        )

    @commands.hybrid_command(name="roletoggle_list", description="List all role-toggle panels configured for this server.")
    async def role_toggle_list(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await self._reply(ctx, "This command can only be used in a server.")
            return

        panels = self.service.list_panels(ctx.guild.id)
        if not panels:
            await self._reply(ctx, "No role-toggle panels are configured for this server.")
            return

        lines = [
            f"- `{p.role_name}` (emoji {p.emoji})"
            for p in panels
        ]
        await self._reply(ctx, "Role-toggle panels:\n" + "\n".join(lines))

    @commands.hybrid_command(name="roletoggle_add", description="Add a new role-toggle panel for this server.")
    @app_commands.describe(
        role_name="Discord role name to create/use.",
        emoji="Emoji users react with to toggle the role (defaults to ✅).",
        title="Embed title (defaults to '<role name> Access').",
    )
    @commands.has_permissions(manage_guild=True)
    async def role_toggle_add(
        self,
        ctx: commands.Context,
        role_name: str,
        emoji: str = DEFAULT_TOGGLE_EMOJI,
        title: str | None = None,
    ) -> None:
        if ctx.guild is None:
            await self._reply(ctx, "This command can only be used in a server.")
            return

        if not self._role_channel_id:
            await self._reply(ctx, "ROLE_CHANNEL_ID is not set. Role toggles are disabled.")
            return

        cleaned_role_name = role_name.strip()
        if not cleaned_role_name:
            await self._reply(ctx, "Role name cannot be empty.")
            return

        effective_title = title.strip() if title and title.strip() else f"{cleaned_role_name} Access"

        self.service.upsert_panel(
            guild_id=ctx.guild.id,
            role_name=cleaned_role_name,
            emoji=emoji,
            title=effective_title,
        )
        await self._reply(ctx, f"Added role-toggle panel for role `{cleaned_role_name}`.")

        channel = await self._get_text_channel(self._role_channel_id)
        if channel is not None:
            await self._ensure_all_panels(ctx.guild, channel)

    @role_toggle_add.error
    async def role_toggle_add_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.MissingPermissions):
            await self._reply(ctx, "You need `Manage Server` permissions to do that.")
            return
        raise error

    @commands.hybrid_command(name="roletoggle_delete", description="Delete a role-toggle panel configuration.")
    @app_commands.describe(
        role_name="Role name of the panel to delete (use /roletoggle_list)",
        delete_discord_role="Also delete the Discord role (only if you really want it gone)",
    )
    @commands.has_permissions(manage_guild=True)
    async def role_toggle_delete(self, ctx: commands.Context, role_name: str, delete_discord_role: bool = True) -> None:
        if ctx.guild is None:
            await self._reply(ctx, "This command can only be used in a server.")
            return

        cleaned_role_name = role_name.strip()
        panel = self.service.get_panel(ctx.guild.id, role_name=cleaned_role_name)
        if panel is None:
            await self._reply(ctx, f"No role-toggle panel found for role `{cleaned_role_name}`.")
            return

        channel = await self._get_text_channel(self._role_channel_id) if self._role_channel_id else None
        if channel is not None and panel.message_id:
            try:
                message = await channel.fetch_message(panel.message_id)
                await message.delete()
            except discord.Forbidden:
                pass
            except discord.NotFound:
                pass
            except discord.HTTPException:
                log.exception("Failed deleting role-toggle message %s", panel.message_id)

        if delete_discord_role:
            # This deletes the real Discord role (removes it from everyone).
            role = discord.utils.get(ctx.guild.roles, name=panel.role_name)
            if role is not None:
                try:
                    await role.delete(reason="Role-toggle deleted by admin")
                except discord.Forbidden:
                    await self._reply(ctx, "Deleted config, but I don't have permission to delete the Discord role.")
                except discord.HTTPException:
                    await self._reply(ctx, "Deleted config, but failed to delete the Discord role (HTTP error).")

        self.service.delete_panel(guild_id=ctx.guild.id, role_name=panel.role_name)
        await self._reply(ctx, f"Deleted role-toggle panel for role `{panel.role_name}`.")

    @role_toggle_delete.error
    async def role_toggle_delete_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.MissingPermissions):
            await self._reply(ctx, "You need `Manage Server` permissions to do that.")
            return
        raise error

    async def _toggle_role_for_member(
        self, *, guild: discord.Guild, user_id: int, role_name: str, should_have_role: bool
    ) -> None:
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            log.warning("Role '%s' does not exist in guild '%s'", role_name, guild.name)
            return

        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                log.warning("Could not fetch member %s in guild '%s'", user_id, guild.name)
                return

        has_role = role in member.roles
        if should_have_role and not has_role:
            await member.add_roles(role, reason="User reacted to role toggle message")
        elif not should_have_role and has_role:
            await member.remove_roles(role, reason="User removed reaction from role toggle message")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if self.bot.user is not None and payload.user_id == self.bot.user.id:
            return
        if payload.guild_id is None:
            return

        # Ignore reactions outside the configured channel.
        if not self._role_channel_id or payload.channel_id != self._role_channel_id:
            return

        panel = self.service.find_matching_panel(
            guild_id=payload.guild_id,
            message_id=payload.message_id,
            emoji=str(payload.emoji),
        )
        if panel is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        try:
            await self._toggle_role_for_member(
                guild=guild, user_id=payload.user_id, role_name=panel.role_name, should_have_role=True
            )
        except discord.Forbidden:
            log.error("Missing permissions to add '%s' via reactions", panel.role_name)
        except Exception:
            log.exception("Failed to add '%s' via reaction", panel.role_name)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return

        # Ignore reactions outside the configured channel.
        if not self._role_channel_id or payload.channel_id != self._role_channel_id:
            return

        panel = self.service.find_matching_panel(
            guild_id=payload.guild_id,
            message_id=payload.message_id,
            emoji=str(payload.emoji),
        )
        if panel is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        try:
            await self._toggle_role_for_member(
                guild=guild, user_id=payload.user_id, role_name=panel.role_name, should_have_role=False
            )
        except discord.Forbidden:
            log.error("Missing permissions to remove '%s' via reactions", panel.role_name)
        except Exception:
            log.exception("Failed to remove '%s' via reaction", panel.role_name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleToggleCog(bot))
