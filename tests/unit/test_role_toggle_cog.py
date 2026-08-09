from types import SimpleNamespace

import pytest

from byte_bot.cogs.role_toggle import RoleToggleCog
from byte_bot.services.role_toggle_service import RoleTogglePanel


def _cog_without_bot() -> RoleToggleCog:
    return RoleToggleCog.__new__(RoleToggleCog)


def test_validate_emoji_accepts_unicode_emoji():
    cog = _cog_without_bot()

    assert cog._validate_emoji("✅") is None


def test_validate_emoji_accepts_custom_emoji():
    cog = _cog_without_bot()

    assert cog._validate_emoji("<:byteclub:123456789012345678>") is None


def test_validate_emoji_rejects_plain_text():
    cog = _cog_without_bot()

    assert cog._validate_emoji("not-an-emoji") is not None


def test_validate_role_name_rejects_everyone_role():
    cog = _cog_without_bot()
    guild = SimpleNamespace(roles=[])

    assert cog._validate_role_name(guild, "@everyone") is not None


def test_validate_role_name_rejects_duplicate_role_names():
    cog = _cog_without_bot()
    guild = SimpleNamespace(roles=[SimpleNamespace(name="ByteClubHQ"), SimpleNamespace(name="ByteClubHQ")])

    assert cog._validate_role_name(guild, "ByteClubHQ") is not None


def test_get_panel_role_uses_role_id():
    cog = _cog_without_bot()
    expected_role = SimpleNamespace(id=100, name="ByteClubHQ")
    same_name_role = SimpleNamespace(id=200, name="ByteClubHQ")
    guild = SimpleNamespace(
        name="Byte Club",
        roles=[same_name_role, expected_role],
        get_role=lambda role_id: expected_role if role_id == expected_role.id else None,
    )
    panel = RoleTogglePanel(
        guild_id=1,
        message_id=2,
        role_id=expected_role.id,
        role_name="ByteClubHQ",
        emoji="✅",
        title="ByteClubHQ Access",
    )

    assert cog._get_panel_role(guild, panel) == expected_role


def test_get_panel_role_requires_stored_role_id():
    cog = _cog_without_bot()
    matching_role = SimpleNamespace(id=100, name="ByteClubHQ")
    guild = SimpleNamespace(
        name="Byte Club",
        roles=[matching_role],
        get_role=lambda role_id: matching_role if role_id == matching_role.id else None,
    )
    panel = RoleTogglePanel(
        guild_id=1,
        message_id=2,
        role_id=None,
        role_name="ByteClubHQ",
        emoji="✅",
        title="ByteClubHQ Access",
    )

    assert cog._get_panel_role(guild, panel) is None


@pytest.mark.asyncio
async def test_setup_role_toggle_panels_does_not_update_new_default_panel():
    cog = _cog_without_bot()
    created = []
    updated = []

    async def create_panel(**kwargs):
        created.append(kwargs)

    async def update_existing_panel(guild, channel, panel):
        updated.append(panel)

    cog.service = SimpleNamespace(list_panels=lambda guild_id: [])
    cog._create_panel = create_panel
    cog._update_existing_panel = update_existing_panel
    guild = SimpleNamespace(id=1, name="Byte Club")
    channel = SimpleNamespace()

    await cog._setup_role_toggle_panels(guild, channel)

    assert len(created) == 1
    assert updated == []


@pytest.mark.asyncio
async def test_resolve_panel_role_recreates_missing_stored_role():
    cog = _cog_without_bot()
    created_role = SimpleNamespace(id=200, name="ByteClubHQ")

    async def create_role(name: str, mentionable: bool):
        assert name == "ByteClubHQ"
        assert mentionable is True
        return created_role

    guild = SimpleNamespace(
        name="Byte Club",
        roles=[],
        get_role=lambda role_id: None,
        create_role=create_role,
    )
    panel = RoleTogglePanel(
        guild_id=1,
        message_id=2,
        role_id=100,
        role_name="ByteClubHQ",
        emoji="✅",
        title="ByteClubHQ Access",
    )

    assert await cog._resolve_panel_role(guild, panel) == created_role


@pytest.mark.asyncio
async def test_update_existing_panel_refreshes_missing_role_id():
    cog = _cog_without_bot()
    created_role = SimpleNamespace(id=200, name="ByteClubHQ")
    edited_messages = []
    reactions = []
    upserted = []

    async def create_role(name: str, mentionable: bool):
        assert name == "ByteClubHQ"
        assert mentionable is True
        return created_role

    async def edit_message(**kwargs):
        edited_messages.append(kwargs)

    async def add_reaction(emoji: str):
        reactions.append(emoji)

    async def fetch_message(message_id: int):
        assert message_id == 2
        return SimpleNamespace(id=2, edit=edit_message, add_reaction=add_reaction)

    def upsert_panel(**kwargs):
        upserted.append(kwargs)
        return RoleTogglePanel(**kwargs)

    cog.service = SimpleNamespace(upsert_panel=upsert_panel, list_memberships=lambda **kwargs: [])
    guild = SimpleNamespace(
        id=1,
        name="Byte Club",
        roles=[],
        get_role=lambda role_id: None,
        create_role=create_role,
    )
    channel = SimpleNamespace(name="roles", fetch_message=fetch_message)
    panel = RoleTogglePanel(
        guild_id=1,
        message_id=2,
        role_id=100,
        role_name="ByteClubHQ",
        emoji="✅",
        title="ByteClubHQ Access",
    )

    assert await cog._update_existing_panel(guild, channel, panel) is True
    assert upserted[0]["role_id"] == created_role.id
    assert reactions == ["✅"]
    assert edited_messages


@pytest.mark.asyncio
async def test_toggle_role_records_membership_before_role_change():
    cog = _cog_without_bot()
    role = SimpleNamespace(id=100, name="ByteClubHQ")
    added_roles = []
    memberships = []

    async def add_roles(role_to_add, reason: str):
        added_roles.append((role_to_add, reason))

    member = SimpleNamespace(id=200, roles=[], add_roles=add_roles)
    guild = SimpleNamespace(
        id=1,
        name="Byte Club",
        get_role=lambda role_id: role if role_id == role.id else None,
        get_member=lambda user_id: member if user_id == member.id else None,
    )
    panel = RoleTogglePanel(
        guild_id=1,
        message_id=2,
        role_id=role.id,
        role_name="ByteClubHQ",
        emoji="âœ…",
        title="ByteClubHQ Access",
    )
    cog.service = SimpleNamespace(set_membership=lambda **kwargs: memberships.append(kwargs))

    await cog._toggle_role_for_member(guild=guild, user_id=member.id, panel=panel, should_have_role=True)

    assert memberships == [{"guild_id": 1, "role_id": 100, "user_id": 200, "should_have_role": True}]
    assert added_roles == [(role, "User reacted to role toggle message")]
