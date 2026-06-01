import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "script" / "weibo_manual_comment_flow.py"
spec = importlib.util.spec_from_file_location("weibo_flow", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
weibo_flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weibo_flow)


def test_emit_evidence_event_formats_single_line_json(capsys):
    weibo_flow.emit_evidence_event("wait", {"context": "initial-load", "result": "networkidle"})

    out = capsys.readouterr().out.strip()
    assert out.startswith("EVIDENCE=")
    payload = json.loads(out.split("=", 1)[1])
    assert payload == {
        "type": "wait",
        "context": "initial-load",
        "result": "networkidle",
    }


def test_build_like_evidence_includes_selector_status_and_state():
    payload = weibo_flow.build_like_evidence("liked-now", "article button[title=\"赞\"]", {"title": "已赞"})

    assert payload["type"] == "like"
    assert payload["status"] == "liked-now"
    assert payload["selector"] == 'article button[title="赞"]'
    assert payload["state"] == {"title": "已赞"}


def test_build_submission_evidence_records_wait_login_and_visibility():
    payload = weibo_flow.build_submission_evidence(
        submit_selector='button:has-text("发送")',
        wait_result='selector:[data-testid="comment-list"]',
        login_required=False,
        comment_visible=True,
    )

    assert payload == {
        "type": "submission",
        "submit_selector": 'button:has-text("发送")',
        "wait_result": 'selector:[data-testid="comment-list"]',
        "login_required": False,
        "comment_visible": True,
    }
