from app.db.models import User
from app.wireguard import reconcile
from app.wireguard.storage import WireGuardPeerRecord


class FakeQuery:
    def __init__(self, values):
        self.values = values

    def all(self):
        return [(value,) for value in sorted(self.values)]


class FakeSession:
    def __init__(self, user_ids, peer_user_ids):
        self.user_ids = set(user_ids)
        self.peer_user_ids = set(peer_user_ids)
        self.rollback_count = 0

    def query(self, column):
        if column is User.id:
            return FakeQuery(self.user_ids)
        if column is WireGuardPeerRecord.user_id:
            return FakeQuery(self.peer_user_ids)
        raise AssertionError(f"Unexpected query column: {column}")

    def rollback(self):
        self.rollback_count += 1


def test_reconciliation_status_counts_missing_and_orphaned_peers(monkeypatch):
    db = FakeSession(user_ids={1, 2, 3}, peer_user_ids={1, 2, 99})
    monkeypatch.setattr(reconcile, "get_wireguard_server", lambda session: object())

    status = reconcile.get_wireguard_reconciliation_status(db)

    assert status == {
        "configured": True,
        "total_users": 3,
        "provisioned_users": 2,
        "missing_users": 1,
        "orphaned_peers": 1,
    }


def test_reconciliation_allocates_only_missing_users(monkeypatch):
    db = FakeSession(user_ids={1, 2, 3}, peer_user_ids={1})
    allocated = []
    monkeypatch.setattr(reconcile, "get_wireguard_server", lambda session: object())

    def allocate(session, *, user_id):
        allocated.append(user_id)
        session.peer_user_ids.add(user_id)

    monkeypatch.setattr(reconcile, "allocate_wireguard_peer", allocate)

    result = reconcile.reconcile_wireguard_peers(db)

    assert allocated == [2, 3]
    assert result["created_peers"] == 2
    assert result["missing_users"] == 0
    assert result["failed_users"] == []


def test_reconciliation_reports_individual_failures(monkeypatch):
    db = FakeSession(user_ids={1, 2}, peer_user_ids=set())
    monkeypatch.setattr(reconcile, "get_wireguard_server", lambda session: object())

    def allocate(session, *, user_id):
        if user_id == 2:
            raise ValueError("subnet exhausted")
        session.peer_user_ids.add(user_id)

    monkeypatch.setattr(reconcile, "allocate_wireguard_peer", allocate)

    result = reconcile.reconcile_wireguard_peers(db)

    assert result["created_peers"] == 1
    assert result["missing_users"] == 1
    assert result["failed_users"] == [{"user_id": 2, "error": "subnet exhausted"}]
    assert db.rollback_count == 1
