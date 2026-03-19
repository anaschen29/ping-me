import pathlib
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

fake_requests = types.ModuleType("requests")


class RequestException(Exception):
    pass


def default_post(*args, **kwargs):
    raise AssertionError("requests.post should be monkeypatched in tests")


fake_requests.RequestException = RequestException
fake_requests.post = default_post
sys.modules.setdefault("requests", fake_requests)

import ping_me.cli as cli


def test_parse_requires_separator():
    try:
        cli.parse_command(["echo", "hi"])
    except ValueError as exc:
        assert "separator" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_main_success_sends_notification(monkeypatch):
    calls = {}

    def fake_run(cmd, shell):
        assert shell is False
        assert cmd == ["echo", "ok"]
        return types.SimpleNamespace(returncode=0)

    def fake_post(url, data, timeout):
        calls["url"] = url
        calls["data"] = data
        calls["timeout"] = timeout

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_TITLE", "my title")
    monkeypatch.setenv("PING_ME_NOTIFY", "all")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(cli.socket, "gethostname", lambda: "host-1")

    rc = cli.main(["--", "echo", "ok"])
    assert rc == 0
    assert calls["url"] == cli.PUSHOVER_URL
    assert calls["timeout"] == 10
    assert calls["data"]["title"] == "my title"
    assert "Host: host-1" in calls["data"]["message"]
    assert "Exit code: 0" in calls["data"]["message"]


def test_main_failure_code_is_preserved(monkeypatch):
    notified = {"called": False}

    def fake_run(cmd, shell):
        return types.SimpleNamespace(returncode=7)

    def fake_post(url, data, timeout):
        notified["called"] = True

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "failure")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.requests, "post", fake_post)

    rc = cli.main(["--", "false"])
    assert rc == 7
    assert notified["called"] is True


@pytest.mark.parametrize(
    ("command", "return_code", "runtime_seconds", "event", "run_payload"),
    [
        (["echo", "ok"], 0, 0.02, "success", {}),
        (["sh", "-c", "exit 3"], 3, 0.03, "failure", {}),
        (["sleep", "0.1"], 0, 0.1, "success", {}),
        (["cmd with spaces", "arg=hello world", "symbols:!@#$%^&*()[]{}"], 4, 0.05, "failure", {}),
        (
            ["python", "-c", "print('noise')"],
            9,
            0.04,
            "failure",
            {"stdout": "out" * 5000, "stderr": "err" * 5000},
        ),
    ],
)
def test_main_parametrized_command_outcomes(
    monkeypatch,
    command,
    return_code,
    runtime_seconds,
    event,
    run_payload,
):
    calls = {}

    def fake_run(cmd, shell):
        assert shell is False
        assert cmd == command
        return types.SimpleNamespace(returncode=return_code, **run_payload)

    def fake_post(url, data, timeout):
        calls["url"] = url
        calls["data"] = data
        calls["timeout"] = timeout

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monotonic_values = iter([100.0, 100.0 + runtime_seconds])

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "all")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(cli.time, "monotonic", lambda: next(monotonic_values))

    rc = cli.main(["--", *command])

    expected_status = "✅ Success" if event == "success" else "❌ Failure"
    message = calls["data"]["message"]

    assert rc == return_code
    assert calls["url"] == cli.PUSHOVER_URL
    assert calls["timeout"] == 10
    assert expected_status in message
    assert f"Exit code: {return_code}" in message
    assert f"Command: {' '.join(command)}" in message
    assert "Runtime:" in message


def test_notify_filter_can_disable(monkeypatch):
    def fake_run(cmd, shell):
        return types.SimpleNamespace(returncode=0)

    def fake_post(url, data, timeout):
        raise AssertionError("should not notify")

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "failure")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.requests, "post", fake_post)

    rc = cli.main(["--", "true"])
    assert rc == 0


def test_interrupt_sends_interrupt_notification(monkeypatch):
    calls = {"message": None}

    def fake_run(cmd, shell):
        raise KeyboardInterrupt()

    def fake_post(url, data, timeout):
        calls["message"] = data["message"]

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "interrupt")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.requests, "post", fake_post)

    rc = cli.main(["--", "sleep", "1"])
    assert rc == 130
    assert "Interrupted" in calls["message"]


def test_device_name_env_overrides_hostname(monkeypatch):
    calls = {}

    def fake_post(url, data, timeout):
        calls["message"] = data["message"]

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_DEVICE_NAME", "my-laptop")
    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(cli.socket, "gethostname", lambda: "host-1")

    cli.send_notification("success", ["echo", "ok"], 0, 1.2)

    assert "Host: my-laptop" in calls["message"]


def test_hostname_fallback_when_device_name_empty(monkeypatch):
    calls = {}

    def fake_post(url, data, timeout):
        calls["message"] = data["message"]

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_DEVICE_NAME", "")
    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(cli.socket, "gethostname", lambda: "host-1")

    cli.send_notification("success", ["echo", "ok"], 0, 1.2)

    assert "Host: host-1" in calls["message"]


def test_missing_credentials_blocks_execution_before_command(monkeypatch, capsys):
    def fake_run(cmd, shell):
        raise AssertionError("subprocess.run should not be called when credentials are missing")

    monkeypatch.delenv("PING_ME_PUSHOVER_TOKEN", raising=False)
    monkeypatch.delenv("PING_ME_PUSHOVER_USER", raising=False)
    monkeypatch.setenv("PING_ME_NOTIFY", "none")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    rc = cli.main(["--", "echo", "ok"])

    captured = capsys.readouterr()
    assert rc == 2
    assert "missing PING_ME_PUSHOVER_TOKEN or PING_ME_PUSHOVER_USER" in captured.err


def test_missing_user_blocks_execution_before_command(monkeypatch):
    def fake_run(cmd, shell):
        raise AssertionError("subprocess.run should not be called when user key is missing")

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.delenv("PING_ME_PUSHOVER_USER", raising=False)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    rc = cli.main(["--", "echo", "ok"])
    assert rc == 2
