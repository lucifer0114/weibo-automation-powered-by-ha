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


def test_build_final_summary_collects_waits_status_and_artifact_path():
    payload = weibo_flow.build_final_summary(
        status="ok",
        initial_wait_result="networkidle",
        submit_wait_result='selector:[data-testid="comment-list"]',
        locate_wait_result="timeout-fallback",
        like_status="liked-now",
        submission_confirmed=True,
        comment_found=True,
        login_required=False,
        primary_mode="contextual",
        final_screenshot="/tmp/comment_context_boxed.png",
    )

    assert payload == {
        "type": "final-summary",
        "status": "ok",
        "wait": {
            "initial_load": "networkidle",
            "after_submit": 'selector:[data-testid="comment-list"]',
            "before_locate_comment": "timeout-fallback",
        },
        "like_status": "liked-now",
        "submission_confirmed": True,
        "comment_found": True,
        "login_required": False,
        "primary_mode": "contextual",
        "final_screenshot": "/tmp/comment_context_boxed.png",
    }


def test_emit_final_summary_formats_single_line_json(capsys):
    weibo_flow.emit_final_summary(
        weibo_flow.build_final_summary(
            status="comment-not-found",
            initial_wait_result="networkidle",
            locate_wait_result="selector:article",
            like_status="already-liked",
            submission_confirmed=False,
            comment_found=False,
            login_required=False,
            primary_mode="full_page",
            final_screenshot="/tmp/comment_raw.png",
        )
    )

    out = capsys.readouterr().out.strip()
    assert out.startswith("FINAL_SUMMARY=")
    payload = json.loads(out.split("=", 1)[1])
    assert payload["type"] == "final-summary"
    assert payload["status"] == "comment-not-found"
    assert payload["wait"]["initial_load"] == "networkidle"
    assert payload["wait"]["before_locate_comment"] == "selector:article"
    assert payload["like_status"] == "already-liked"
    assert payload["final_screenshot"] == "/tmp/comment_raw.png"
