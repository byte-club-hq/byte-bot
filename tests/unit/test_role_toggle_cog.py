from types import SimpleNamespace

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
