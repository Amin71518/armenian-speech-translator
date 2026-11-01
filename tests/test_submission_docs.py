from scripts.check_submission import documentation_link_errors


def test_delivery_links_resolve_from_each_document_directory(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (tmp_path / 'README.md').write_text('[Evidence](docs/EXPERIMENTS.md)')
    (docs / 'EXPERIMENTS.md').write_text(
        '[Setup](../README.md) [Checks](VALIDATION.md#checks) [Online](https://example.com)')
    (docs / 'VALIDATION.md').write_text('# Checks')
    names = ('README.md', 'docs/EXPERIMENTS.md', 'docs/VALIDATION.md')
    assert documentation_link_errors(tmp_path, names) == []


def test_delivery_audit_reports_removed_targets_and_missing_required_files(tmp_path):
    (tmp_path / 'README.md').write_text('[Old report](TESTS.md)')
    assert documentation_link_errors(tmp_path, ('README.md', 'docs/VALIDATION.md')) == [
        {'file': 'README.md', 'target': 'TESTS.md'},
        {'file': 'docs/VALIDATION.md', 'target': 'required document missing'},
    ]
