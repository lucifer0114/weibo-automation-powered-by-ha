import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "script" / "weibo_manual_comment_flow.py"
spec = importlib.util.spec_from_file_location("weibo_flow", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
weibo_flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weibo_flow)


class FakeLocator:
    def __init__(self, name, count=1, visible=True, children=None):
        self.name = name
        self._count = count
        self.visible = visible
        self.children = children or {}
        self.clicked = 0
        self.filled = []

    @property
    def first(self):
        return self

    def count(self):
        return self._count

    def wait_for(self, state=None, timeout=None):
        if self._count == 0 or not self.visible:
            raise RuntimeError(f"{self.name} not visible")

    def is_visible(self, timeout=None):
        return self._count > 0 and self.visible

    def click(self, timeout=None):
        if self._count == 0:
            raise RuntimeError(f"{self.name} not clickable")
        self.clicked += 1

    def fill(self, text, timeout=None):
        self.filled.append(text)

    def press(self, key, timeout=None):
        return None

    def type(self, text, delay=None, timeout=None):
        self.filled.append(text)

    def locator(self, selector):
        return self.children.get(selector, FakeLocator(f"{self.name}->{selector}", count=0))


class FakePage:
    def __init__(self, selectors=None, texts=None):
        self.selectors = selectors or {}
        self.texts = texts or {}

    def locator(self, selector):
        return self.selectors.get(selector, FakeLocator(selector, count=0))

    def get_by_text(self, text):
        return self.texts.get(text, FakeLocator(f"text:{text}", count=0))


class FakeCommentsRoot(FakeLocator):
    pass


def test_detects_login_required_page_from_login_markers():
    page = FakePage(
        selectors={
            'input[name="username"]': FakeLocator('username'),
        },
        texts={
            '登录': FakeLocator('login-text'),
        },
    )

    assert weibo_flow.page_requires_login(page) is True


def test_logged_in_page_is_not_misclassified_as_login_required():
    page = FakePage(
        selectors={
            'textarea': FakeLocator('textarea'),
        }
    )

    assert weibo_flow.page_requires_login(page) is False


def test_find_comment_locator_is_scoped_to_comments_root_not_whole_page():
    comments_root = FakeCommentsRoot(
        'comments-root',
        children={
            'text=目标评论': FakeLocator('scoped-comment'),
        },
    )
    page = FakePage(
        selectors={
            '.WB_feed_detail, [data-testid="comment-list"], .woo-box-flex.woo-box-alignCenter.woo-box-justifyBetween': comments_root,
            'text=目标评论': FakeLocator('wrong-global-match'),
        }
    )

    locator, selector = weibo_flow.find_comment_in_comments_root(page, '目标评论')

    assert locator.name == 'scoped-comment'
    assert selector == 'text=目标评论'


def test_open_comment_panel_and_submit_comment_use_different_buttons():
    page = FakePage(
        selectors={
            '[aria-label="评论"]': FakeLocator('open-comment-button'),
            'button:has-text("发送")': FakeLocator('submit-button'),
        }
    )

    open_selector = weibo_flow.open_comment_panel(page)
    submit_selector = weibo_flow.submit_comment(page)

    assert open_selector == '[aria-label="评论"]'
    assert submit_selector == 'button:has-text("发送")'


def test_verify_submission_requires_visible_comment_match():
    page_without_comment = FakePage(selectors={})
    assert weibo_flow.verify_comment_submission(page_without_comment, '目标评论') is False

    comments_root = FakeCommentsRoot(
        'comments-root',
        children={
            'text=目标评论': FakeLocator('scoped-comment'),
        },
    )
    page_with_comment = FakePage(
        selectors={
            '.WB_feed_detail, [data-testid="comment-list"], .woo-box-flex.woo-box-alignCenter.woo-box-justifyBetween': comments_root,
        }
    )
    assert weibo_flow.verify_comment_submission(page_with_comment, '目标评论') is True
