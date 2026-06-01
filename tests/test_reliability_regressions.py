import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "script" / "weibo_manual_comment_flow.py"
spec = importlib.util.spec_from_file_location("weibo_flow", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
weibo_flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weibo_flow)


class FakeLocator:
    def __init__(self, name, count=1, visible=True, eval_results=None, children=None):
        self.name = name
        self._count = count
        self.visible = visible
        self.eval_results = list(eval_results or [])
        self.children = children or {}
        self.clicked = 0
        self.filled = []
        self.pressed = []
        self.typed = []
        self.waited = []

    @property
    def first(self):
        return self

    def count(self):
        return self._count

    def wait_for(self, state=None, timeout=None):
        self.waited.append((state, timeout))
        if self._count == 0 or not self.visible:
            raise RuntimeError(f"{self.name} not visible")

    def is_visible(self, timeout=None):
        return self._count > 0 and self.visible

    def click(self, timeout=None):
        self.clicked += 1

    def fill(self, text, timeout=None):
        self.filled.append(text)

    def press(self, key, timeout=None):
        self.pressed.append(key)

    def type(self, text, delay=None, timeout=None):
        self.typed.append(text)

    def locator(self, selector):
        return self.children.get(selector, FakeLocator(f"{self.name}->{selector}", count=0))

    def evaluate(self, js, arg=None):
        if self.eval_results:
            return self.eval_results.pop(0)
        return None


class FakeTextHandle(FakeLocator):
    pass


class FakePage:
    def __init__(self, selectors=None, texts=None):
        self.selectors = selectors or {}
        self.texts = texts or {}
        self.wait_calls = []

    def locator(self, selector):
        return self.selectors.get(selector, FakeLocator(selector, count=0))

    def get_by_text(self, text):
        return self.texts.get(text, FakeTextHandle(f"text:{text}", count=0))

    def wait_for_timeout(self, ms):
        self.wait_calls.append(ms)


class FakeSortLocator(FakeLocator):
    def __init__(self, name, page, count=1, visible=True):
        super().__init__(name, count=count, visible=visible)
        self.page = page

    def click(self, timeout=None):
        super().click(timeout=timeout)
        self.page.sort_text_visible = True


class FakeSortPage(FakePage):
    def __init__(self, sort_text_visible=False):
        super().__init__()
        self.sort_text_visible = sort_text_visible
        self.sort_button = FakeSortLocator("sort-button", self)
        self.active_sort = FakeLocator('active-sort', count=1, visible=True)

    def locator(self, selector):
        if selector in weibo_flow.TIME_SORT_ACTIVE_SELECTORS:
            return self.active_sort if self.sort_text_visible else FakeLocator(selector, count=0)
        return super().locator(selector)

    def get_by_text(self, text):
        if text == "按时间":
            if self.sort_text_visible:
                return FakeTextHandle("sort-text", count=1, visible=True)
            return self.sort_button
        return super().get_by_text(text)


def test_fill_comment_box_skips_generic_editors_and_uses_composer_markers():
    wrong_editor = FakeLocator('[contenteditable="true"]')
    right_editor = FakeLocator('[data-testid="comment-composer"] [contenteditable="true"]')
    page = FakePage(
        selectors={
            '[data-testid="comment-composer"] textarea': FakeLocator('missing-textarea', count=0),
            '[data-testid="comment-composer"] [contenteditable="true"]': right_editor,
            '[contenteditable="true"]': wrong_editor,
        }
    )

    locator, selector = weibo_flow.fill_comment_box(page, '测试评论')

    assert locator is right_editor
    assert selector == '[data-testid="comment-composer"] [contenteditable="true"]'
    assert wrong_editor.clicked == 0
    assert right_editor.filled == ['测试评论']


def test_ensure_post_liked_checks_title_and_class_state():
    like_locator = FakeLocator(
        'like-button',
        eval_results=[
            {'className': '', 'countClass': '', 'title': '已赞', 'text': ''},
        ],
    )
    page = FakePage(selectors={'article button[title="赞"]': like_locator})

    status, selector, state = weibo_flow.ensure_post_liked(page)

    assert status == 'already-liked'
    assert selector == 'article button[title="赞"]'
    assert state['title'] == '已赞'
    assert like_locator.clicked == 0


def test_switches_sort_to_time_and_verifies_result():
    page = FakeSortPage(sort_text_visible=False)

    assert weibo_flow.ensure_time_sort(page) is True
    assert page.sort_button.clicked == 1


def test_ensure_time_sort_returns_false_when_text_never_visible():
    class NeverVisiblePage(FakePage):
        def __init__(self):
            super().__init__()
            self.sort_button = FakeLocator('sort-button', count=1, visible=True)

        def locator(self, selector):
            if selector in weibo_flow.TIME_SORT_ACTIVE_SELECTORS:
                return FakeLocator(selector, count=0)
            return super().locator(selector)

        def get_by_text(self, text):
            if text == '按时间':
                return self.sort_button
            return super().get_by_text(text)

    page = NeverVisiblePage()
    assert weibo_flow.ensure_time_sort(page) is False


def test_choose_highlight_box_prefers_expanded_box_but_falls_back_to_text_box():
    text_box = {'x': 100, 'y': 200, 'width': 80, 'height': 20, 'right': 180, 'bottom': 220}
    expanded_box = {'x': 90, 'y': 190, 'width': 200, 'height': 120, 'right': 290, 'bottom': 310}

    assert weibo_flow.choose_highlight_box(text_box, expanded_box) == expanded_box
    assert weibo_flow.choose_highlight_box(text_box, None) == text_box


def test_normalize_crop_box_clamps_and_preserves_minimum_size():
    raw_crop = {'x': -20, 'y': -10, 'right': 50, 'bottom': 40}
    highlight_box = {'x': 10, 'y': 15, 'width': 30, 'height': 25, 'right': 40, 'bottom': 40}

    normalized = weibo_flow.normalize_crop_box(raw_crop, highlight_box)

    assert normalized['x'] == 0
    assert normalized['y'] == 0
    assert normalized['right'] >= highlight_box['right']
    assert normalized['bottom'] >= highlight_box['bottom']
