import pathlib
import sys
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

fake_requests = types.ModuleType("requests")


class RequestException(Exception):
    pass


def default_post(*args, **kwargs):
    raise AssertionError("requests.post should be monkeypatched in tests")


fake_requests.RequestException = RequestException
fake_requests.post = default_post
sys.modules.setdefault("requests", fake_requests)

from ping_me import notify
import ping_me.cli as cli


def test_notify_is_importable_from_package_root():
    assert callable(notify)


def test_notify_default_status_is_info(monkeypatch):
    calls = {}

    def fake_post(url, data, timeout):
        calls["message"] = data["message"]

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "info")
    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(cli.socket, "gethostname", lambda: "host-1")

    notify("epoch done")
    assert calls["message"].splitlines()[0] == "ℹ️ Info"
    assert "Message: epoch done" in calls["message"]


def test_notify_uses_inherited_job_name(monkeypatch):
    calls = {}

    def fake_post(url, data, timeout):
        calls["message"] = data["message"]

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "info")
    monkeypatch.setenv(cli.PING_ME_JOB_NAME, "Inherited Job")
    monkeypatch.setattr(cli.requests, "post", fake_post)

    notify("epoch done")
    assert calls["message"].splitlines()[0] == "Job Inherited Job: ℹ️ Info"


def test_notify_explicit_job_name_overrides_inherited(monkeypatch):
    calls = {}

    def fake_post(url, data, timeout):
        calls["message"] = data["message"]

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "info")
    monkeypatch.setenv(cli.PING_ME_JOB_NAME, "Inherited Job")
    monkeypatch.setattr(cli.requests, "post", fake_post)

    notify("epoch done", job_name="Explicit Job")
    assert calls["message"].splitlines()[0] == "Job Explicit Job: ℹ️ Info"


def test_main_injects_context_env_for_subprocess(monkeypatch):
    seen_env = {}

    def fake_run(cmd, shell, env):
        seen_env.update(env)
        return types.SimpleNamespace(returncode=0)

    def fake_post(url, data, timeout):
        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "none")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.requests, "post", fake_post)

    rc = cli.main(["--name", "Train Job", "--", "echo", "ok"])
    assert rc == 0
    assert seen_env[cli.PING_ME_CONTEXT_ACTIVE] == "1"
    assert seen_env[cli.PING_ME_JOB_NAME] == "Train Job"
    assert seen_env[cli.PING_ME_PARENT_COMMAND] == "echo ok"


def test_terminal_notify_filter_matches_terminal_events(monkeypatch):
    events = []

    def fake_post(url, data, timeout):
        events.append(data["message"].splitlines()[0])

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("PING_ME_PUSHOVER_TOKEN", "token")
    monkeypatch.setenv("PING_ME_PUSHOVER_USER", "user")
    monkeypatch.setenv("PING_ME_NOTIFY", "terminal")
    monkeypatch.setattr(cli.requests, "post", fake_post)

    cli.send_notification("info", ["echo", "hi"], 0, 0.1, detail_message="step")
    cli.send_notification("success", ["echo", "ok"], 0, 0.1)
    cli.send_notification("failure", ["false"], 1, 0.1)
    cli.send_notification("interrupt", ["sleep", "1"], 130, 0.1)
    assert events == ["✅ Success", "❌ Failure", "⚠️ Interrupted"]
