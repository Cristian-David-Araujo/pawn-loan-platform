"""Refusing to serve production with the credentials printed in the README.

`admin` / `admin123` and the JWT key `change_this_in_production` appear in `.env.example`, in
the README and in the seed. Convenient in development, an unlocked front door in production —
and a published signing key means anyone can mint their own token for any user.
"""

import pytest

from src.infrastructure.config.settings import Settings, assert_production_secrets


def _settings(**overrides) -> Settings:
    base = {
        "app_env": "production",
        "admin_password": "a-real-password",
        "jwt_secret_key": "a-real-secret-key-long-enough-to-sign",
    }
    base.update(overrides)
    return Settings(**base)


def test_development_is_left_alone() -> None:
    """The defaults exist so a clone runs with no setup; that must keep working."""
    assert_production_secrets(_settings(app_env="development", admin_password="admin123",
                                       jwt_secret_key="change_this_in_production"))


def test_production_refuses_the_default_admin_password() -> None:
    with pytest.raises(RuntimeError) as error:
        assert_production_secrets(_settings(admin_password="admin123"))
    assert "ADMIN_PASSWORD" in str(error.value)


def test_production_refuses_the_default_signing_key() -> None:
    with pytest.raises(RuntimeError) as error:
        assert_production_secrets(_settings(jwt_secret_key="change_this_in_production"))
    assert "JWT_SECRET_KEY" in str(error.value)


def test_production_names_every_value_still_unset() -> None:
    """One restart, one message, not a game of whack-a-mole."""
    with pytest.raises(RuntimeError) as error:
        assert_production_secrets(
            _settings(admin_password="admin123", jwt_secret_key="change_this_in_production")
        )
    message = str(error.value)
    assert "ADMIN_PASSWORD" in message and "JWT_SECRET_KEY" in message


def test_production_with_real_secrets_starts() -> None:
    assert_production_secrets(_settings())


def test_the_env_name_is_matched_loosely() -> None:
    """Deployments spell it `Production` or with stray whitespace; the guard still applies."""
    with pytest.raises(RuntimeError):
        assert_production_secrets(_settings(app_env=" Production ", admin_password="admin123"))
