from app.wireguard import lifecycle


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def rollback(self):
        pass


def test_reconcile_provisions_created_users_and_releases_deleted_users(monkeypatch):
    allocated = []
    deleted = []

    monkeypatch.setattr(lifecycle, "SessionLocal", FakeSession)
    monkeypatch.setattr(lifecycle, "get_wireguard_server", lambda db: object())
    monkeypatch.setattr(
        lifecycle,
        "allocate_wireguard_peer",
        lambda db, *, user_id: allocated.append(user_id),
    )
    monkeypatch.setattr(
        lifecycle,
        "delete_wireguard_peer",
        lambda db, user_id: deleted.append(user_id),
    )

    lifecycle.reconcile_wireguard_users(
        created_user_ids={10, 11},
        deleted_user_ids={11, 12},
    )

    assert deleted == [11, 12]
    assert allocated == [10]


def test_reconcile_skips_provisioning_until_server_is_configured(monkeypatch):
    allocated = []

    monkeypatch.setattr(lifecycle, "SessionLocal", FakeSession)
    monkeypatch.setattr(lifecycle, "get_wireguard_server", lambda db: None)
    monkeypatch.setattr(
        lifecycle,
        "allocate_wireguard_peer",
        lambda db, *, user_id: allocated.append(user_id),
    )

    lifecycle.reconcile_wireguard_users(created_user_ids={10}, deleted_user_ids=set())

    assert allocated == []
