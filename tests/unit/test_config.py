from rhoai_mcp.config import Settings


class TestSettings:
    def test_defaults(self):
        """Settings should have sensible defaults."""
        settings = Settings(
            _env_file=None,  # don't read .env in tests
        )
        assert settings.default_time_range == "5m"
        assert settings.log_level == "INFO"
        assert settings.request_timeout == 30.0

    def test_env_override(self, monkeypatch):
        """Environment variables should override defaults."""
        monkeypatch.setenv("THANOS_URL", "https://thanos.example.com")
        monkeypatch.setenv("DEFAULT_TIME_RANGE", "15m")
        settings = Settings(_env_file=None)
        assert settings.thanos_url == "https://thanos.example.com"
        assert settings.default_time_range == "15m"

    def test_all_backend_urls_optional(self):
        """All backend URLs should be optional (auto-detected later)."""
        settings = Settings(_env_file=None)
        assert settings.thanos_url is None
        assert settings.alertmanager_url is None
        assert settings.loki_url is None
        assert settings.grafana_url is None

    def test_is_in_cluster_false_by_default(self):
        """Should detect as external when no SA token exists."""
        settings = Settings(_env_file=None)
        assert isinstance(settings.is_in_cluster, bool)
