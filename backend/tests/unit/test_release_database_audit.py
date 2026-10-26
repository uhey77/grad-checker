import pytest

from scripts import check_release_database as audit


def uri(*, direct=False, host=None, database="grad-checker", query="sslmode=require"):
    selected = host or (audit.DIRECT_HOST if direct else audit.POOLED_HOST)
    return f"postgresql://owner:do-not-log@{selected}/{database}?{query}"


@pytest.mark.parametrize("direct", [False, True])
def test_known_production_endpoint_and_tls_are_required(direct):
    audit.validate_target(uri(direct=direct), direct=direct)
    for value in [
        uri(direct=not direct),
        uri(host="ep-rehearsal.ap-southeast-1.aws.neon.tech"),
        uri(database="neondb"),
        uri(query="sslmode=disable"),
        uri(query="sslmode=require&options=-csearch_path%3Dother"),
        uri(query="sslmode=require&host=other.example"),
    ]:
        with pytest.raises(ValueError):
            audit.validate_target(value, direct=direct)


def test_failed_inspection_never_prints_secret_or_exception(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", uri())
    monkeypatch.setenv("DIRECT_DATABASE_URL", uri(direct=True))

    def fail(*_args, **_kwargs):
        raise RuntimeError(uri())

    monkeypatch.setattr(audit, "inspect_target", fail)
    assert audit.main([]) == 1
    output = capsys.readouterr()
    assert "do-not-log" not in output.out + output.err
    assert "postgresql://" not in output.out + output.err


def test_both_sources_must_pass_before_reporting_success(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", uri())
    monkeypatch.setenv("DIRECT_DATABASE_URL", uri(direct=True))
    checked = []
    monkeypatch.setattr(
        audit, "inspect_target", lambda _value, *, direct: checked.append(direct)
    )
    assert audit.main([]) == 0
    assert checked == [False, True]
    assert '"rows": 1738' in capsys.readouterr().out


def test_secret_manager_failure_is_suppressed(monkeypatch, capsys):
    def fail(*_args, **_kwargs):
        raise RuntimeError("secret-manager-do-not-log")

    monkeypatch.setattr(audit, "secret_manager_value", fail)
    assert audit.main(["--secret-manager"]) == 1
    assert "secret-manager-do-not-log" not in capsys.readouterr().out
