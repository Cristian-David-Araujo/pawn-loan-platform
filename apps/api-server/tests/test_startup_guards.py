"""Refusing to serve production with the signing key printed in the README.

`change_this_in_production` is in `.env.example` and in the README, so keeping it means anyone
can mint a token for any user. There is no safe way to serve with it, the fix is a config
change the operator already controls, and no data is at stake — which is what makes a fatal
guard the right shape here.

The counter-example matters just as much and has its own test below: `ADMIN_PASSWORD` only
seeds the admin on first boot, so it goes stale the moment the operator changes their password
in the app. Refusing to start over a stale value takes a deployment down for nothing.
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


def test_production_refuses_the_default_signing_key() -> None:
    with pytest.raises(RuntimeError) as error:
        assert_production_secrets(_settings(jwt_secret_key="change_this_in_production"))
    assert "JWT_SECRET_KEY" in str(error.value)


def test_a_stale_admin_password_variable_never_blocks_a_deployment() -> None:
    """The stored password is the real credential, and the operator owns it.

    This guard used to reject `ADMIN_PASSWORD=admin123` and stopped a production deployment
    whose admin had long since set a strong password from the users screen — a false positive
    with no security benefit, and blind to the case that actually matters.
    """
    assert_production_secrets(_settings(admin_password="admin123"))


def test_production_with_a_real_signing_key_starts() -> None:
    assert_production_secrets(_settings())


def test_the_env_name_is_matched_loosely() -> None:
    """Deployments spell it `Production` or with stray whitespace; the guard still applies."""
    with pytest.raises(RuntimeError):
        assert_production_secrets(
            _settings(app_env=" Production ", jwt_secret_key="change_this_in_production")
        )
