"""الواجهة مربوطة بـ /api/i18n — المرحلة 5 (§4.6) end-to-end.

الكاتالوغ كان موجود في الـ backend وما يستهلكو حتى شي: الواجهة كلها عربية
صلب و dir ما يتبدّلش. هنا نتحقّقو من الربط الفعلي ومن أن كل مفتاح مستعمل
في الواجهة موجود في كل locale.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from core import i18n
from starlette.testclient import TestClient

STATIC = Path(__file__).resolve().parent.parent / "web" / "static"
APP_JS = (STATIC / "genio-app.js").read_text(encoding="utf-8")
INDEX_HTML = (STATIC / "index.html").read_text(encoding="utf-8")

JS_KEY = re.compile(r"""\bt\(\s*["']([a-zA-Z0-9_.]+)["']""")
HTML_KEY = re.compile(r"""data-i18n(?:-placeholder)?=["']([a-zA-Z0-9_.]+)["']""")


# ---------------------------------------------------------------------------
# الكاتالوغ
# ---------------------------------------------------------------------------
def test_every_string_exists_in_every_locale():
    report = i18n.key_report()
    assert report["ok"] is True, report["missing"]


def test_ui_keys_are_in_the_catalogue():
    js_keys = set(JS_KEY.findall(APP_JS))
    html_keys = set(HTML_KEY.findall(INDEX_HTML))
    missing = sorted((js_keys | html_keys) - set(i18n.STRINGS))
    assert missing == [], f"مفاتيح مستعملة في الواجهة وما فمّاش في الكاتالوغ: {missing}"


def test_ui_catalogue_is_not_arabic_only():
    """كل مفتاح متاع الواجهة لازم عندو ترجمة فرنسية وإنجليزية فعليّة."""
    ui_keys = set(JS_KEY.findall(APP_JS)) | set(HTML_KEY.findall(INDEX_HTML))
    untranslated = [
        key
        for key in sorted(ui_keys)
        if i18n.STRINGS[key]["fr"] in ("", i18n.STRINGS[key]["en"])
        or i18n.STRINGS[key]["en"] == i18n.STRINGS[key]["ar-TN"]
    ]
    # أسماء علم/تقنية تتشابه بين اللغات (ZIP, Git, DevOps, Code…) مقبولة
    allowed = {"studio.zip", "onb.opt.git", "onb.opt.devops", "onb.opt.code", "onb.opt.chat", "onb.opt.en"}
    assert [key for key in untranslated if key not in allowed] == []


# ---------------------------------------------------------------------------
# الـ API
# ---------------------------------------------------------------------------
def test_every_locale_exposes_dir_and_strings(server):
    _owner(server)  # الحسابات موجودة = /api يحتاج جلسة، أما /api/i18n عمومي
    anonymous = TestClient(server.app, client=("127.0.0.1", 50000))

    expected = {"ar-TN": "rtl", "ar": "rtl", "fr": "ltr", "en": "ltr"}
    for locale, direction in expected.items():
        response = anonymous.get(f"/api/i18n/{locale}")
        assert response.status_code == 200, locale
        body = response.json()
        assert body["dir"] == direction, locale
        assert body["id"] == locale
        assert body["strings"]["studio.title"]
        assert body["strings"]["onb.q.occupation.title"]


def test_switching_locale_changes_the_text(server):
    anonymous = TestClient(server.app, client=("127.0.0.1", 50000))
    ar = anonymous.get("/api/i18n/ar-TN").json()
    fr = anonymous.get("/api/i18n/fr").json()
    en = anonymous.get("/api/i18n/en").json()

    assert ar["strings"]["auth.title.login"] != fr["strings"]["auth.title.login"]
    assert fr["strings"]["auth.title.login"] != en["strings"]["auth.title.login"]
    assert fr["strings"]["studio.new"] != ar["strings"]["studio.new"]


def test_unknown_locale_is_rejected(server):
    anonymous = TestClient(server.app, client=("127.0.0.1", 50000))
    assert anonymous.get("/api/i18n/de").status_code == 400


# ---------------------------------------------------------------------------
# الواجهة: الربط نفسه
# ---------------------------------------------------------------------------
def test_app_js_fetches_the_catalogue_and_applies_dir():
    assert "/api/i18n/" in APP_JS
    assert 'setAttribute("dir"' in APP_JS
    assert 'setAttribute("lang"' in APP_JS
    assert "data-i18n" in APP_JS
    assert "genio_locale" in APP_JS  # الاختيار يتفكّر


def test_overlays_carry_translation_hooks():
    for key in ("auth.email", "auth.password", "onb.intro", "studio.title", "studio.create"):
        assert f'data-i18n="{key}"' in INDEX_HTML, key
    assert 'id="gioLocale"' in INDEX_HTML
    assert 'id="gioLocaleStudio"' in INDEX_HTML


def test_locale_switch_redraws_the_visible_overlay():
    """العنوان والـ hint متاع الـ auth يتكتبو بـ JS، لازم يتعاودو بعد تبديل اللغة."""
    assert "function renderAuthTexts" in APP_JS
    assert "renderAuthTexts()" in APP_JS
    assert 'if (auth && !auth.hidden) renderAuthTexts();' in APP_JS


def test_all_six_v8_tabs_are_wired():
    """الـ 6 tabs متاع v8 (office/ide/logs/terminal/rag/admin) من الكاتالوغ."""
    expected = {
        "tab-office": "v8.tab.office",
        "tab-ide": "v8.tab.ide",
        "tab-ops": "v8.tab.ops",
        "tab-term": "v8.tab.term",
        "tab-rag": "v8.tab.rag",
        "tab-admin": "v8.tab.admin",
    }
    for tab_id, key in expected.items():
        assert f'id="{tab_id}"' in INDEX_HTML, tab_id
        assert f'data-i18n="{key}"' in INDEX_HTML, key
        assert key in i18n.STRINGS, key


def test_v8_panels_have_no_hardcoded_label_left_out():
    """لكل tab عناصر مرجعية (تسميات، أزرار، placeholders) مربوطة بالكاتالوغ."""
    required = [
        "v8.office.cam_top", "v8.office.act_meet", "v8.office.swarm", "v8.office.send",
        "v8.ide.zip", "v8.ide.save", "v8.ide.refresh",
        "v8.ops.refresh",
        "v8.term.run",
        "v8.rag.save", "v8.rag.docs",
        "v8.admin.save", "v8.admin.pull", "v8.admin.sync",
    ]
    for key in required:
        assert f'data-i18n="{key}"' in INDEX_HTML, key


def test_v8_placeholders_are_translated_too():
    for key in ("v8.office.prompt_ph", "v8.ide.zip_ph", "v8.term.ph", "v8.rag.ph"):
        assert f'data-i18n-placeholder="{key}"' in INDEX_HTML, key


GT_KEY = re.compile(r"""\bgt\(\s*["']([a-zA-Z0-9_.]+)["']""")
ARABIC = re.compile(r"[\u0600-\u06FF]")


def _inline_v8_script() -> str:
    """السكريبت الداخلي متاع v8 (المحرك 3D + الـ chat + الإدارة)."""
    start = INDEX_HTML.index("const HQ_LAYOUT")
    return INDEX_HTML[start:]


def _strip_js_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//[^\n]*", "", source)


def _tab_markup() -> str:
    """HTML ساكن متاع الـ 6 tabs (بلا السكريبت و بلا الـ overlays)."""
    return INDEX_HTML[INDEX_HTML.index('id="tab-office"') : INDEX_HTML.index("const HQ_LAYOUT")]


def test_every_dynamic_v8_string_comes_from_the_catalogue():
    """كل نص ديناميكي في التابات (غرف، حالات، رسائل) يتحلّ بـ gt(key)."""
    keys = set(GT_KEY.findall(INDEX_HTML))
    assert len(keys) >= 25, sorted(keys)
    missing = sorted(key for key in keys if key not in i18n.STRINGS)
    assert missing == [], f"gt() ب keys ما فمّاش في الكاتالوغ: {missing}"


def test_no_arabic_literal_left_in_the_v8_script():
    """ما فمّاش نص عربي صلب في كود v8 — العربية تجي من الكاتالوغ."""
    code = _strip_js_comments(_inline_v8_script())
    leftovers = sorted({line.strip() for line in code.splitlines() if ARABIC.search(line)})
    assert leftovers == [], "نص عربي صلب باقي في السكريبت: " + str(leftovers[:5])


class _ArabicTextFinder(HTMLParser):
    """يلقى النصوص العربية اللي ما هيش داخل عنصر مربوط بمفتاح."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[bool] = []  # لكل عنصر: هل عندو data-i18n*؟
        self.unwired: list[str] = []

    def handle_starttag(self, tag, attrs):
        names = dict(attrs)
        wired = any(name.startswith("data-i18n") for name in names)
        if tag not in ("br", "img", "input", "meta", "link", "hr"):
            self.stack.append(wired)
        elif ARABIC.search(names.get("placeholder", "")) and not wired:
            self.unwired.append(f"placeholder غير مربوط: {names.get('placeholder')}")

    def handle_endtag(self, tag):
        if tag not in ("br", "img", "input", "meta", "link", "hr") and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if ARABIC.search(data) and not any(self.stack):
            self.unwired.append(data.strip())


def test_every_arabic_node_in_the_tabs_is_wired_to_a_key():
    """ما فمّاش نص عربي في التابات بلا مفتاح (نص، HTML، ولا placeholder)."""
    finder = _ArabicTextFinder()
    finder.feed(_tab_markup())
    assert finder.unwired == [], "عناصر عربية بلا مفتاح: " + str(finder.unwired[:5])




def test_no_v8_key_missing_in_any_locale():
    v8_keys = [key for key in i18n.STRINGS if key.startswith("v8.")]
    assert len(v8_keys) >= 80
    missing = {
        key: [code for code, value in i18n.STRINGS[key].items() if not (value or "").strip()]
        for key in v8_keys
    }
    assert {k: v for k, v in missing.items() if v} == {}



def test_onboarding_labels_come_from_the_catalogue():
    """أسئلة الـ onboarding ما عادش فيهم نص عربي صلب في الـ JS."""
    assert "onb.q.occupation.title" in APP_JS
    assert "onb.opt.student" in APP_JS
    # العنوان القديم المصلّب تنجّمو نلقاوه غير كـ fallback في الكاتالوغ
    assert 'title: "شنوّة تخدم؟"' not in APP_JS


# ---------------------------------------------------------------------------
# مساعد: الحساب الأوّل
# ---------------------------------------------------------------------------
def _owner(server):
    from starlette.testclient import TestClient as Client

    client = Client(server.app, client=("127.0.0.1", 50000))
    client.post(
        "/api/auth/bootstrap",
        json={"email": "owner@hitech.tn", "password": "genio-test-pass"},
    )
    return client
