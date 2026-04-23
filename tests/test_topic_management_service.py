from __future__ import annotations

from datetime import date

from models import DifficultyLevel, Revision
from services import SchedulerService, SubjectService, TopicService


def _build_services(session, today_value: date) -> tuple[SubjectService, TopicService]:
    scheduler = SchedulerService(session, today_provider=lambda: today_value)
    return SubjectService(session), TopicService(session, scheduler=scheduler)


def test_subject_service_crud_flow(session) -> None:
    subject_service, _ = _build_services(session, date(2026, 4, 9))

    subject = subject_service.create_subject(
        name="Mathematics",
        color_tag="#123456",
        exam_date=date(2026, 6, 1),
        description="STEM core subject",
    )
    updated = subject_service.update_subject(subject.id, name="Advanced Mathematics", color_tag="#654321")
    subjects = subject_service.list_subjects()

    assert updated.name == "Advanced Mathematics"
    assert updated.color_tag == "#654321"
    assert [item.id for item in subjects] == [subject.id]


def test_topic_service_auto_schedules_first_revision(session) -> None:
    subject_service, topic_service = _build_services(session, date(2026, 4, 9))
    subject = subject_service.create_subject(name="Physics", exam_date=date(2026, 4, 11))

    topic = topic_service.create_topic(subject_id=subject.id, name="Magnetism", difficulty=DifficultyLevel.HARD)
    session.commit()

    revisions = session.query(Revision).filter(Revision.topic_id == topic.id).all()
    assert len(revisions) == 1
    assert topic.exam_date == date(2026, 4, 11)
    assert topic.fsrs_due_date == date(2026, 4, 10)
    assert revisions[0].scheduled_date == date(2026, 4, 9)


def test_topic_tree_and_leaf_traversal(session) -> None:
    subject_service, topic_service = _build_services(session, date(2026, 4, 9))
    subject = subject_service.create_subject(name="Biology")

    root = topic_service.create_topic(subject_id=subject.id, name="Cell Biology", auto_schedule=False)
    child_a = topic_service.create_topic(subject_id=subject.id, name="Cell Membrane", parent_topic_id=root.id, auto_schedule=False)
    child_b = topic_service.create_topic(subject_id=subject.id, name="Mitochondria", parent_topic_id=root.id, auto_schedule=False)
    leaf = topic_service.create_topic(subject_id=subject.id, name="ATP Synthesis", parent_topic_id=child_b.id, auto_schedule=False)

    tree = topic_service.get_topic_tree(subject.id)
    leaves = topic_service.get_leaf_topics(subject.id)

    assert len(tree) == 1
    assert tree[0].name == "Cell Biology"
    assert {node.name for node in tree[0].children} == {"Cell Membrane", "Mitochondria"}
    assert {topic.id for topic in leaves} == {child_a.id, leaf.id}


def test_topic_update_and_delete_flow(session) -> None:
    subject_service, topic_service = _build_services(session, date(2026, 4, 9))
    subject = subject_service.create_subject(name="History")
    topic = topic_service.create_topic(subject_id=subject.id, name="World War I", auto_schedule=False)

    updated = topic_service.update_topic(
        topic.id,
        name="World War I Overview",
        difficulty=DifficultyLevel.EASY,
        notes="Focus on timeline",
        exam_date=date(2026, 5, 1),
    )
    topic_service.delete_topic(topic.id)
    session.commit()

    assert updated.name == "World War I Overview"
    assert updated.difficulty == DifficultyLevel.EASY
    assert topic_service.get_topic(topic.id) is None
