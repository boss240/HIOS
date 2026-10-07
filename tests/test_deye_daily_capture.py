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
        'providerCode': None, 'stage': 'unknown',
    }


def test_duplicate_scope_rejected_before_provider_access(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'unused')
    monkeypatch.setenv('HIOS_CAPTURE_SUBJECT', 'test')
    monkeypatch.setenv('HIOS_CAPTURE_TENANT', 'test')
    monkeypatch.setenv('HIOS_CAPTURE_PLANTS', '["same", "same"]')
    with patch.object(deye_daily_capture, 'DeyeReadOnlyClient') as client:
        assert deye_daily_capture.run() == 1
        client.assert_not_called()


def test_authentication_stage_is_reported_without_raw_endpoint(capsys):
    from app.deye_openapi import DeyeApiError
    error = DeyeApiError('secret message', endpoint='/v1.0/account/token',
                         provider_code='2101025')
    with patch.object(deye_daily_capture, 'main', side_effect=error):
        assert deye_daily_capture.run() == 1
    body = json.loads(capsys.readouterr().out)
    assert body['stage'] == 'authentication'
    assert body['providerCode'] == '2101025'
    assert 'endpoint' not in body


def test_unrecognized_endpoint_is_not_logged(capsys):
    from app.deye_openapi import DeyeApiError
    error = DeyeApiError('private', endpoint='/v1.0/account/token?secret=private')
    with patch.object(deye_daily_capture, 'main', side_effect=error):
        assert deye_daily_capture.run() == 1
    output = capsys.readouterr().out
    assert 'private' not in output
    assert json.loads(output)['stage'] == 'unknown'
