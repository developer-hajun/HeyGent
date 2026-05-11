from types import SimpleNamespace

from app.api.http.work import _unresolved_blocker_work_ids


class FakeWorkRepository:
    def __init__(self, *, relations, works):
        self._relations = relations
        self._works = works

    def list_relations(self, work_id: str):
        return [
            relation
            for relation in self._relations
            if relation.source_work_id == work_id or relation.target_work_id == work_id
        ]

    def get_work(self, work_id: str):
        return self._works.get(work_id)


def relation(source: str, target: str, relation_type: str = "blocks"):
    return SimpleNamespace(source_work_id=source, target_work_id=target, relation_type=relation_type)


def work(status: str):
    return SimpleNamespace(status=status)


def test_unresolved_blocker_work_ids_ignores_completed_blockers():
    repository = FakeWorkRepository(
        relations=[relation("blocker-1", "target-1"), relation("blocker-2", "target-1"), relation("target-1", "related-1", "related")],
        works={"blocker-1": work("done"), "blocker-2": work("cancelled")},
    )

    assert _unresolved_blocker_work_ids(repository, "target-1") == []


def test_unresolved_blocker_work_ids_returns_non_done_blockers():
    repository = FakeWorkRepository(
        relations=[
            relation("blocker-1", "target-1"),
            relation("blocker-2", "target-1"),
            relation("target-1", "other-1"),
        ],
        works={"blocker-1": work("todo")},
    )

    assert _unresolved_blocker_work_ids(repository, "target-1") == ["blocker-1", "blocker-2"]
