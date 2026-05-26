from __future__ import annotations

from dataclasses import dataclass
import logging

import discord

from byte_bot.services.database_service import DatabaseService

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoleTogglePanel:
    guild_id: int
    message_id: int | None
    role_name: str
    emoji: str
    title: str


DEFAULT_ROLE_NAME = "ByteClubHQ"
DEFAULT_TOGGLE_EMOJI = "\u2705"
DEFAULT_TOGGLE_TITLE = "ByteClubHQ Access"


class RoleToggleService:
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service

    def list_panels(self, guild_id: int) -> list[RoleTogglePanel]:
        with self.database_service.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT guild_id, message_id, role_name, emoji, title
                FROM role_toggle_panels
                WHERE guild_id = ?
                ORDER BY role_name ASC
                """
                ,
                (guild_id,),
            ).fetchall()

        return [
            RoleTogglePanel(
                guild_id=row["guild_id"],
                message_id=row["message_id"],
                role_name=row["role_name"],
                emoji=row["emoji"],
                title=row["title"],
            )
            for row in rows
        ]

    def get_panel(self, guild_id: int, *, role_name: str = DEFAULT_ROLE_NAME) -> RoleTogglePanel | None:
        with self.database_service.get_connection() as connection:
            row = connection.execute(
                """
                SELECT guild_id, message_id, role_name, emoji, title
                FROM role_toggle_panels
                WHERE guild_id = ? AND role_name = ?
                """,
                (guild_id, role_name),
            ).fetchone()

        if row is None:
            return None

        return RoleTogglePanel(
            guild_id=row["guild_id"],
            message_id=row["message_id"],
            role_name=row["role_name"],
            emoji=row["emoji"],
            title=row["title"],
        )

    def upsert_panel(
        self,
        *,
        guild_id: int,
        role_name: str = DEFAULT_ROLE_NAME,
        emoji: str = DEFAULT_TOGGLE_EMOJI,
        title: str = DEFAULT_TOGGLE_TITLE,
        message_id: int | None = None,
    ) -> RoleTogglePanel:
        with self.database_service.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO role_toggle_panels (guild_id, message_id, role_name, emoji, title)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, role_name) DO UPDATE SET
                        message_id = COALESCE(excluded.message_id, role_toggle_panels.message_id),
                        emoji = excluded.emoji,
                        title = excluded.title
                    """,
                    (guild_id, message_id, role_name, emoji, title),
                )

        return self.get_panel(guild_id, role_name=role_name)  # type: ignore[return-value]

    def delete_panel(self, *, guild_id: int, role_name: str) -> None:
        with self.database_service.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    DELETE FROM role_toggle_panels
                    WHERE guild_id = ? AND role_name = ?
                    """,
                    (guild_id, role_name),
                )

    def set_message_id(
        self, *, guild_id: int, role_name: str, message_id: int | None
    ) -> None:
        with self.database_service.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE role_toggle_panels
                    SET message_id = ?
                    WHERE guild_id = ? AND role_name = ?
                    """,
                    (message_id, guild_id, role_name),
                )

    def find_matching_panel(
        self, *, guild_id: int, message_id: int, emoji: str
    ) -> RoleTogglePanel | None:
        with self.database_service.get_connection() as connection:
            row = connection.execute(
                """
                SELECT guild_id, message_id, role_name, emoji, title
                FROM role_toggle_panels
                WHERE guild_id = ? AND message_id = ? AND emoji = ?
                """,
                (guild_id, message_id, emoji),
            ).fetchone()

        if row is None:
            return None

        return RoleTogglePanel(
            guild_id=row["guild_id"],
            message_id=row["message_id"],
            role_name=row["role_name"],
            emoji=row["emoji"],
            title=row["title"],
        )

    async def ensure_role(self, guild: discord.Guild, role_name: str) -> discord.Role:
        role = discord.utils.get(guild.roles, name=role_name)
        if role is not None:
            return role

        role = await guild.create_role(name=role_name, mentionable=True)
        log.info("Created role '%s' in guild '%s'", role_name, guild.name)
        return role
