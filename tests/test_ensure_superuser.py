import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


pytestmark = pytest.mark.django_db


def test_creates_superuser_from_env(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "a-strong-password")
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

    call_command("ensure_superuser")

    user = get_user_model().objects.get(username="admin")
    assert user.is_superuser and user.is_staff
    assert user.email == "admin@example.com"
    assert user.check_password("a-strong-password")


def test_is_idempotent_and_syncs_password(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "first-password")
    call_command("ensure_superuser")

    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "rotated-password")
    call_command("ensure_superuser")

    assert get_user_model().objects.filter(username="admin").count() == 1
    user = get_user_model().objects.get(username="admin")
    assert user.check_password("rotated-password")


def test_skips_when_env_missing(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    call_command("ensure_superuser")

    assert get_user_model().objects.count() == 0
