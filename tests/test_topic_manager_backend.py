from studyflow_backend.service import StudyFlowBackend


def test_curriculum_summary_and_subject_tree_are_available(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "topic_manager_state.json")

    assert backend.curriculumSummary["total_topics"] >= 1
    assert len(backend.curriculumSummary["stats"]) == 4
    assert len(backend.curriculumSubjects) >= 1


def test_upsert_topic_creates_child_topic_and_task(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "topic_manager_state.json")
    parent_topic = backend._topics[0]
    original_task_count = len(backend._tasks)

    backend.upsertTopic("", "Leaf Topic", parent_topic["subject"], "Medium", parent_topic["id"], "Child notes")

    created_topic = next(topic for topic in backend._topics if topic["name"] == "Leaf Topic")
    created_task = next(task for task in backend._tasks if task["topic"] == "Leaf Topic")

    assert created_topic["parent_topic_id"] == parent_topic["id"]
    assert created_task["subject"] == parent_topic["subject"]
    assert len(backend._tasks) == original_task_count + 1


def test_suggest_and_import_topics_work(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "topic_manager_state.json")
    suggestion = backend.suggestTopicDifficulty("Organic reaction mechanisms")
    original_topic_count = len(backend._topics)

    backend.importTopics("Topic Alpha\nTopic Beta", "Physics", False)

    assert suggestion["confidence"] >= 0.0
    assert len(backend._topics) == original_topic_count + 2
    assert any(topic["name"] == "Topic Alpha" for topic in backend._topics)


def test_import_topics_accepts_subject_and_difficulty_columns(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "topic_manager_state.csv_state.json")

    backend.importTopics(
        "subject,topic,difficulty\nPhysics,Optics,Hard\nChemistry,Hydrocarbons,Easy",
        "",
        True,
    )

    imported_topics = {topic["name"]: topic for topic in backend._topics}

    assert imported_topics["Optics"]["subject"] == "Physics"
    assert imported_topics["Optics"]["difficulty"] == "Hard"
    assert imported_topics["Hydrocarbons"]["subject"] == "Chemistry"
    assert imported_topics["Hydrocarbons"]["difficulty"] == "Easy"
    assert any(subject["subjectName"] == "Chemistry" for subject in backend.curriculumSubjects)


def test_release_style_store_path_starts_without_demo_data(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "studyflow_data.json")

    assert backend.curriculumSummary["total_topics"] == 0
    assert backend.curriculumSubjects == []
