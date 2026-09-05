"""Regression test for Mistral's namespace-package client export."""


def test_mistral_client_resolves_from_supported_sdk_layout():
    from ai.providers.mistral import _mistral_client_class, _sdk_error

    assert _sdk_error() is None
    assert _mistral_client_class().__name__ == "Mistral"
