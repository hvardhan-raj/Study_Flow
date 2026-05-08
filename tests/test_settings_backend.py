from datetime import timedelta

from db.repositories import TopicRepository
from studyflow_backend.service import StudyFlowBackend


def test_schedule_settings_persist_in_app_settings(tmp_path) -> None:
    store_path = tmp_path / "settings_state.json"

    backend = StudyFlowBackend(store_path)
    assert backend.scheduleSettings["daily_time_minutes"] == 120
    assert backend.scheduleSettings["preferred_time"] == "18:00"

    backend.updateScheduleSetting("daily_time_minutes", "150")
    backend.updateScheduleSetting("preferred_time", "19:30")

    reloaded = StudyFlowBackend(store_path)
    assert reloaded.scheduleSettings["daily_time_minutes"] == 150
    assert reloaded.scheduleSettings["preferred_time"] == "19:30"


def test_daily_limit_increase_immediately_updates_schedule_views(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "settings_state.json")
    today = backend._today + timedelta(days=365)
    backend._today_provider = lambda: today

    backend.updateScheduleSetting("daily_time_minutes", "60")
    with backend._db() as db:
        topic_repo = TopicRepository(db)
        subject = topic_repo.create_subject("Biology")
        topic_a = topic_repo.create_topic(subject_id=subject.id, name="Photosynthesis", difficulty="hard")
        topic_b = topic_repo.create_topic(subject_id=subject.id, name="Respiration", difficulty="hard")
        scheduler = backend._scheduler(db)
        scheduler.create_first_revision(topic_a.id, scheduled_for=today)
        scheduler.create_first_revision(topic_b.id, scheduled_for=today)

    backend.selectToday()
    before_topics = {session["topic"] for session in backend.selectedDaySessions}
    assert "Respiration" not in before_topics

    backend.updateScheduleSetting("daily_time_minutes", "180")

    after_topics = {session["topic"] for session in backend.selectedDaySessions}
    assert {"Photosynthesis", "Respiration"} <= after_topics
