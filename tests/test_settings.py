from config.settings import settings


def test_settings_create_expected_paths() -> None:
    settings.ensure_directories()

    assert settings.database_path.parent.exists()
    assert settings.local_model_path.parent.exists()
    assert settings.log_file.parent.exists()

