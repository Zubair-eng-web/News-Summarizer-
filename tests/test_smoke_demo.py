from scripts.smoke_demo import CHECKS, main, run_checks


def test_all_pass_when_statuses_are_expected():
    def fake(method, path):
        for _, m, p, allowed in CHECKS:
            if m == method and p == path:
                return sorted(allowed)[0], ""
        return 404, ""

    results = run_checks(fake)
    assert len(results) == len(CHECKS)
    assert all(ok for _, ok, _ in results)


def test_unexpected_status_fails():
    results = run_checks(lambda m, p: (500, ""))
    assert not any(ok for _, ok, _ in results)


def test_network_error_is_reported_not_raised():
    def boom(method, path):
        raise OSError("no network")

    results = run_checks(boom)
    assert all((not ok) and "no network" in detail for _, ok, detail in results)


def test_main_without_url_returns_2(capsys):
    assert main([]) == 2
    assert "Usage" in capsys.readouterr().out
