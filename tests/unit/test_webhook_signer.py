"""Webhook signature vector tests."""

import pytest

from engineering_influence.interaction.webhooks import WebhookSigner


def test_webhook_signer_round_trip() -> None:
    signer = WebhookSigner(b"secret")
    signature = signer.sign(b'{"event":"pipeline.started"}')

    assert signature == "v1=3e875d20c21123a0d05218477ba8c8da4d543b8cfe89ba0db09774fc6709b8d0"
    assert signer.verify(b'{"event":"pipeline.started"}', signature)
    assert not signer.verify(b'{"event":"pipeline.completed"}', signature)
    assert not signer.verify(b'{"event":"pipeline.started"}', "v1=bad")


def test_webhook_signer_requires_secret() -> None:
    with pytest.raises(ValueError, match="secret"):
        WebhookSigner(b"")
