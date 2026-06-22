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


def test_role_toggle_service_tracks_membership_state(database_path):
    service = RoleToggleService(DatabaseService(database_path))

    service.set_membership(guild_id=123, role_id=456, user_id=789, should_have_role=True)
    service.set_membership(guild_id=123, role_id=456, user_id=999, should_have_role=False)

    memberships = service.list_memberships(guild_id=123, role_id=456)

    assert [membership.user_id for membership in memberships] == [789, 999]
    assert memberships[0].should_have_role is True
    assert memberships[1].should_have_role is False


def test_role_toggle_service_updates_membership_state(database_path):
    service = RoleToggleService(DatabaseService(database_path))

    service.set_membership(guild_id=123, role_id=456, user_id=789, should_have_role=True)
    service.set_membership(guild_id=123, role_id=456, user_id=789, should_have_role=False)

    [membership] = service.list_memberships(guild_id=123, role_id=456)

    assert membership.should_have_role is False


def test_role_toggle_service_deletes_memberships_for_role(database_path):
    service = RoleToggleService(DatabaseService(database_path))
    service.set_membership(guild_id=123, role_id=456, user_id=789, should_have_role=True)
    service.set_membership(guild_id=123, role_id=999, user_id=789, should_have_role=True)

    service.delete_memberships(guild_id=123, role_id=456)

    assert service.list_memberships(guild_id=123, role_id=456) == []
    assert len(service.list_memberships(guild_id=123, role_id=999)) == 1
