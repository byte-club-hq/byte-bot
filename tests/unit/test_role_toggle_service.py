from byte_bot.services.database_service import DatabaseService
from byte_bot.services.role_toggle_service import RoleToggleService


def test_role_toggle_service_upserts_and_reads_panel(database_path):
    service = RoleToggleService(DatabaseService(database_path))

    panel = service.upsert_panel(
        guild_id=123,
        message_id=456,
        role_id=789,
        role_name="ByteClubHQ",
        emoji="✅",
        title="ByteClubHQ Access",
    )

    assert panel.guild_id == 123
    assert panel.message_id == 456
    assert panel.role_id == 789
    assert panel.role_name == "ByteClubHQ"
    assert panel.emoji == "✅"
    assert panel.title == "ByteClubHQ Access"
    assert service.get_panel(123, role_name="ByteClubHQ") == panel


def test_role_toggle_service_updates_panel_without_losing_ids(database_path):
    service = RoleToggleService(DatabaseService(database_path))
    service.upsert_panel(
        guild_id=123,
        message_id=456,
        role_id=789,
        role_name="ByteClubHQ",
        emoji="✅",
        title="ByteClubHQ Access",
    )

    updated_panel = service.upsert_panel(
        guild_id=123,
        role_name="ByteClubHQ",
        emoji="🔥",
        title="Updated Access",
    )

    assert updated_panel.message_id == 456
    assert updated_panel.role_id == 789
    assert updated_panel.emoji == "🔥"
    assert updated_panel.title == "Updated Access"


def test_role_toggle_service_finds_custom_emoji_panel(database_path):
    service = RoleToggleService(DatabaseService(database_path))
    custom_emoji = "<:byteclub:123456789012345678>"
    service.upsert_panel(
        guild_id=123,
        message_id=456,
        role_id=789,
        role_name="ByteClubHQ",
        emoji=custom_emoji,
        title="ByteClubHQ Access",
    )

    panel = service.find_matching_panel(guild_id=123, message_id=456, emoji=custom_emoji)

    assert panel is not None
    assert panel.emoji == custom_emoji


def test_role_toggle_service_lists_panels_by_role_name(database_path):
    service = RoleToggleService(DatabaseService(database_path))
    service.upsert_panel(guild_id=123, role_name="Z Role", emoji="✅", title="Z Access")
    service.upsert_panel(guild_id=123, role_name="A Role", emoji="🔥", title="A Access")

    panels = service.list_panels(123)

    assert [panel.role_name for panel in panels] == ["A Role", "Z Role"]


def test_role_toggle_service_deletes_panel(database_path):
    service = RoleToggleService(DatabaseService(database_path))
    service.upsert_panel(guild_id=123, role_name="ByteClubHQ", emoji="✅", title="ByteClubHQ Access")

    service.delete_panel(guild_id=123, role_name="ByteClubHQ")

    assert service.get_panel(123, role_name="ByteClubHQ") is None
