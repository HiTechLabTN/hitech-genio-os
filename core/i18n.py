"""Locales, direction and UI strings — Plan v1 §4.6.

Every screen string lives here, not in the HTML, so the UI can switch language
without touching markup. ``dir`` is data, not a guess: ar-TN/ar are RTL, fr/en
are LTR, and the UI must apply it on the container, while code, filenames and
numbers keep their own direction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_LOCALE = "ar-TN"

LOCALES: Dict[str, Dict[str, str]] = {
    "ar-TN": {"label": "دارجة", "dir": "rtl", "html_lang": "ar"},
    "ar": {"label": "العربية", "dir": "rtl", "html_lang": "ar"},
    "fr": {"label": "Français", "dir": "ltr", "html_lang": "fr"},
    "en": {"label": "English", "dir": "ltr", "html_lang": "en"},
}

STRINGS: Dict[str, Dict[str, str]] = {
    "app.title": {
        "ar-TN": "جينيو OS — استوديو الذكاء الاصطناعي",
        "ar": "جينيو OS — استوديو الذكاء الاصطناعي",
        "fr": "Genio OS — Studio d'IA",
        "en": "Genio OS — AI Studio",
    },
    "nav.chat": {"ar-TN": "المحادثة", "ar": "المحادثة", "fr": "Chat", "en": "Chat"},
    "nav.ide": {"ar-TN": "محرّر الكود", "ar": "محرر الكود", "fr": "Éditeur", "en": "Editor"},
    "nav.terminal": {"ar-TN": "الطرفية", "ar": "الطرفية", "fr": "Terminal", "en": "Terminal"},
    "nav.memory": {"ar-TN": "الذاكرة", "ar": "الذاكرة", "fr": "Mémoire", "en": "Memory"},
    "nav.rag": {"ar-TN": "قاعدة المعرفة", "ar": "قاعدة المعرفة", "fr": "Connaissances", "en": "Knowledge"},
    "nav.admin": {"ar-TN": "الإدارة", "ar": "الإدارة", "fr": "Administration", "en": "Admin"},
    "action.send": {"ar-TN": "ابعث", "ar": "أرسل", "fr": "Envoyer", "en": "Send"},
    "action.save": {"ar-TN": "سجّل", "ar": "احفظ", "fr": "Enregistrer", "en": "Save"},
    "action.cancel": {"ar-TN": "ألغي", "ar": "إلغاء", "fr": "Annuler", "en": "Cancel"},
    "action.delete": {"ar-TN": "امحي", "ar": "احذف", "fr": "Supprimer", "en": "Delete"},
    "action.approve": {"ar-TN": "وافق", "ar": "موافقة", "fr": "Approuver", "en": "Approve"},
    "action.reject": {"ar-TN": "ارفض", "ar": "رفض", "fr": "Refuser", "en": "Reject"},
    "action.login": {"ar-TN": "ادخل", "ar": "تسجيل الدخول", "fr": "Connexion", "en": "Sign in"},
    "action.logout": {"ar-TN": "اخرج", "ar": "تسجيل الخروج", "fr": "Déconnexion", "en": "Sign out"},
    "onboarding.start": {
        "ar-TN": "يالله نعرفوك",
        "ar": "لنتعرف عليك",
        "fr": "Faisons connaissance",
        "en": "Let's get to know you",
    },
    "onboarding.skip": {"ar-TN": "تعدّى توّا", "ar": "تخطّي", "fr": "Passer", "en": "Skip"},
    "status.online": {"ar-TN": "متّصل", "ar": "متصل", "fr": "En ligne", "en": "Online"},
    "status.offline": {"ar-TN": "ماشي متّصل", "ar": "غير متصل", "fr": "Hors ligne", "en": "Offline"},
    "status.loading": {"ar-TN": "جاري التحميل…", "ar": "جارٍ التحميل…", "fr": "Chargement…", "en": "Loading…"},
    "status.ready": {"ar-TN": "واجد", "ar": "جاهز", "fr": "Prêt", "en": "Ready"},
    "status.error": {"ar-TN": "خطأ", "ar": "خطأ", "fr": "Erreur", "en": "Error"},
    "mode.chat": {"ar-TN": "وضع المحادثة", "ar": "وضع المحادثة", "fr": "Mode chat", "en": "Chat mode"},
    "mode.dev": {"ar-TN": "وضع التطوير", "ar": "وضع التطوير", "fr": "Mode dev", "en": "Dev mode"},
    "mode.enterprise": {
        "ar-TN": "وضع المؤسسة",
        "ar": "وضع المؤسسة",
        "fr": "Mode entreprise",
        "en": "Enterprise mode",
    },
    "auth.email": {"ar-TN": "الإيميل", "ar": "البريد الإلكتروني", "fr": "E-mail", "en": "Email"},
    "auth.password": {"ar-TN": "كلمة السر", "ar": "كلمة المرور", "fr": "Mot de passe", "en": "Password"},
    "auth.denied": {
        "ar-TN": "ما عندكش الحق",
        "ar": "لا تملك الصلاحية",
        "fr": "Accès refusé",
        "en": "Access denied",
    },
    "tool.approval_needed": {
        "ar-TN": "لازم موافقة قبل التنفيذ",
        "ar": "تلزم موافقة قبل التنفيذ",
        "fr": "Approbation requise",
        "en": "Approval required",
    },
    "shell.disabled": {
        "ar-TN": "الطرفية مقفولة",
        "ar": "الطرفية مغلقة",
        "fr": "Terminal désactivé",
        "en": "Terminal disabled",
    },
}


class LocaleError(ValueError):
    """Unknown locale."""


def locale_info(locale: str, default: Optional[str] = None) -> Dict[str, str]:
    code = locale if locale in LOCALES else (default or DEFAULT_LOCALE)
    if code not in LOCALES:
        raise LocaleError(f"locale غير معروف: {locale}")
    return {"id": code, **LOCALES[code]}


def catalogue(locale: str) -> Dict[str, Any]:
    info = locale_info(locale)
    strings = {key: values.get(info["id"], values.get(DEFAULT_LOCALE, "")) for key, values in STRINGS.items()}
    return {**info, "strings": strings, "count": len(strings)}


def translate(key: str, locale: str = DEFAULT_LOCALE) -> str:
    values = STRINGS.get(key)
    if not values:
        return key
    return values.get(locale) or values.get(DEFAULT_LOCALE) or key


def available() -> List[Dict[str, str]]:
    return [{"id": code, **info} for code, info in LOCALES.items()]


def key_report() -> Dict[str, Any]:
    """Audit for CI: every key must exist in every locale, non-empty."""
    missing = {
        key: [code for code in LOCALES if not (values.get(code) or "").strip()]
        for key, values in STRINGS.items()
    }
    missing = {key: codes for key, codes in missing.items() if codes}
    return {"keys": len(STRINGS), "locales": list(LOCALES), "missing": missing, "ok": not missing}
