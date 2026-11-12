from offerbot.app import load_environment
from offerbot.config import ConfigurationError, Settings


def test_load_environment_reads_bot_token_from_explicit_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BOT_TOKEN=123456:token-from-env-file\n"
        "OWNER_ID=123456789\n"
        "SUB_CHANNEL=easynftch\n",
        encoding="utf-8",
    )
    for key in ("BOT_TOKEN", "OWNER_ID", "ADMIN_IDS", "SUB_CHANNEL", "DB_PATH"):
        monkeypatch.delenv(key, raising=False)

    assert load_environment(env_file) is True

    settings = Settings.from_env()
    assert settings.bot_token == "123456:token-from-env-file"
    assert settings.owner_id == 123456789
    assert settings.sub_channel == "easynftch"


def test_existing_process_environment_takes_precedence_over_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BOT_TOKEN=token-from-file\n"
        "OWNER_ID=123456789\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BOT_TOKEN", "token-from-deployment")
    monkeypatch.setenv("OWNER_ID", "123456789")

    load_environment(env_file)

    assert Settings.from_env().bot_token == "token-from-deployment"


def test_bot_token_is_required_and_never_has_a_source_default(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("OWNER_ID", "123456789")

    try:
        Settings.from_env()
    except ConfigurationError as exc:
        assert "BOT_TOKEN is required" in str(exc)
    else:
        raise AssertionError("Settings.from_env must reject missing BOT_TOKEN")



def test_default_env_file_is_resolved_from_project_root_not_current_directory(tmp_path, monkeypatch):
    from offerbot import app

    project_root = tmp_path / "project"
    elsewhere = tmp_path / "elsewhere"
    project_root.mkdir()
    elsewhere.mkdir()
    (project_root / ".env").write_text(
        "BOT_TOKEN=token-from-project-root\n"
        "OWNER_ID=987654321\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app, "PROJECT_ROOT", project_root)
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("OWNER_ID", raising=False)

    assert app.load_environment() is True
    settings = Settings.from_env()
    assert settings.bot_token == "token-from-project-root"
    assert settings.owner_id == 987654321
