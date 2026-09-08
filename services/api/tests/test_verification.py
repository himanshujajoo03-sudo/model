"""Verification outbox contract tests."""
from pathlib import Path


def test_verification_uses_transactional_outbox():
    text = Path(__file__).resolve().parents[1].joinpath('routers/verification.py').read_text()
    assert 'enqueue(conn' in text
    assert 'publish_verification_action' not in text
    assert 'new_status' in text


def test_outbox_uses_stable_message_identity():
    text = Path(__file__).resolve().parents[1].joinpath('services/verification_outbox.py').read_text()
    assert '"message_id": outbox_id' in text
    assert 'verification_outbox' in text
