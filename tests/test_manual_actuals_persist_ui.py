from pathlib import Path

def test_manual_actuals_commit_is_explicit():
    root=Path(__file__).resolve().parents[1]
    assert 'commitManualActuals' in (root/'web/index.html').read_text(encoding='utf-8')
    script=(root/'web/manual-actuals-persist.js').read_text(encoding='utf-8')
    assert 'payload.confirmPersist = true' in script
    assert '/dashboard/actuals/manual-import/file-commit' in script
    assert 'xlsxBase64' in script
