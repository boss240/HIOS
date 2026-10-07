import json
from unittest.mock import patch

from app import deye_daily_capture


def test_failure_output_does_not_include_exception_secrets(capsys):
    error = RuntimeError('password=private-value device=private-serial')
    with patch.object(deye_daily_capture, 'main', side_effect=error):
        assert deye_daily_capture.run() == 1
    output = capsys.readouterr().out
    assert 'private-value' not in output
    assert 'private-serial' not in output
    assert json.loads(output) == {
        'outcome': 'collection_failed', 'errorClass': 'RuntimeError',
        'providerCode': None,
    }


def test_duplicate_scope_rejected_before_provider_access(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'unused')
    monkeypatch.setenv('HIOS_CAPTURE_SUBJECT', 'test')
    monkeypatch.setenv('HIOS_CAPTURE_TENANT', 'test')
    monkeypatch.setenv('HIOS_CAPTURE_PLANTS', '["same", "same"]')
    with patch.object(deye_daily_capture, 'DeyeReadOnlyClient') as client:
        assert deye_daily_capture.run() == 1
        client.assert_not_called()
