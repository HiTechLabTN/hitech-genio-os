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


# ---------------------------------------------------------------------------
# UI strings (genio-app.js overlays) — same catalogue, so the UI has one source.
# Compact table: (ar-TN, ar, fr, en).
# ---------------------------------------------------------------------------
_UI_STRINGS: Dict[str, tuple] = {
    "auth.title.login": ("ادخل للمنصّة", "تسجيل الدخول", "Connexion", "Sign in"),
    "auth.title.bootstrap": ("أوّل حساب (المالك)", "أول حساب (المالك)", "Premier compte", "First account"),
    "auth.hint.login": ("الإيميل وكلمة السر متاعك.", "أدخل بريدك وكلمة المرور.", "Votre e-mail et mot de passe.", "Your email and password."),
    "auth.hint.bootstrap": (
        "ما فمّاش حتى حساب. اعمل حساب المالك الأوّل — بعدو المنصّة تولّي محمية بالجلسة.",
        "لا يوجد حساب. أنشئ حساب المالك الأول — بعده تصبح المنصة محمية بالجلسة.",
        "Aucun compte. Créez le compte propriétaire — ensuite la plateforme exige une session.",
        "No account yet. Create the owner account — the platform then requires a session.",
    ),
    "auth.hint.no_api": ("ما قدرناش نتواصلو مع الـ API.", "تعذّر الاتصال بالـ API.", "Impossible de joindre l'API.", "Could not reach the API."),
    "auth.hint.session": ("الجلسة ما تثبّتش — عاود ادخل.", "لم تثبت الجلسة — أعد الدخول.", "Session non établie — reconnectez-vous.", "Session not established — sign in again."),
    "auth.hint.owner": ("الحساب الأوّل يولّي owner.", "الحساب الأول يصبح owner.", "Le premier compte devient propriétaire.", "The first account becomes the owner."),
    "auth.name": ("الاسم", "الاسم", "Nom", "Name"),
    "auth.create": ("اعمل الحساب", "أنشئ الحساب", "Créer le compte", "Create account"),
    "onb.intro": ("«يلا نعرفوك»", "«لنتعرّف عليك»", "«Faisons connaissance»", "«Let's get to know you»"),
    "onb.back": ("اللي قبل", "السابق", "Retour", "Back"),
    "onb.next": ("التالي", "التالي", "Suivant", "Next"),
    "onb.finish": ("كمّل ✓", "إنهاء ✓", "Terminer ✓", "Finish ✓"),
    "onb.q.occupation.title": ("شنوّة تخدم؟", "ما هي مهنتك؟", "Quel est votre métier ?", "What do you do?"),
    "onb.q.occupation.hint": ("نختارو الشخصية والأدوات على أساسها.", "نختار الشخصية والأدوات بناءً عليها.", "La persona et les outils en dépendent.", "The persona and tools follow from it."),
    "onb.q.goals.title": ("شنوّة تحب تعمل بالـ AI؟", "ماذا تريد أن تفعل بالـ AI؟", "Que voulez-vous faire avec l'IA ?", "What do you want to do with AI?"),
    "onb.q.goals.hint": ("تنجّم تختار أكثر من وحدة.", "يمكنك اختيار أكثر من واحد.", "Plusieurs choix possibles.", "Pick as many as you need."),
    "onb.q.level.title": ("مستواك التقني؟", "مستواك التقني؟", "Votre niveau technique ?", "Your technical level?"),
    "onb.q.level.hint": ("يحدّد صلاحيات الطرفية والـ sandbox.", "يحدد صلاحيات الطرفية والـ sandbox.", "Définit les droits du terminal et du sandbox.", "Sets terminal and sandbox permissions."),
    "onb.q.register.title": ("لغة الردود؟", "لغة الردود؟", "Langue des réponses ?", "Reply language?"),
    "onb.q.register.hint": (
        "الدارجة، الفصحى، الفرنسية ولا الإنجليزية — تبدّل وقت ما تحب.",
        "الدارجة، الفصحى، الفرنسية أو الإنجليزية — قابلة للتغيير.",
        "Derja, arabe standard, français ou anglais — modifiable.",
        "Derja, standard Arabic, French or English — changeable.",
    ),
    "onb.q.env.title": ("وين يخدم الـ AI؟", "أين يعمل الـ AI؟", "Où tourne l'IA ?", "Where does the AI run?"),
    "onb.q.env.hint": ("محلي = بياناتك ما تخرجش.", "محلي = بياناتك لا تخرج.", "Local = vos données ne sortent pas.", "Local = your data never leaves."),
    "onb.q.sensitivity.title": ("عندك بيانات حسّاسة؟", "هل لديك بيانات حساسة؟", "Avez-vous des données sensibles ?", "Any sensitive data?"),
    "onb.q.sensitivity.hint": ("عالٍ = الـ shell والشبكة يتقفلو.", "عالٍ = يُغلق الـ shell والشبكة.", "Élevé = terminal et réseau fermés.", "High = shell and network closed."),
    "onb.q.tools.title": ("أهم أداة تحب تلقاها جاهزة؟", "أهم أداة تريدها جاهزة؟", "Quel outil voulez-vous prêt ?", "Which tool do you want ready?"),
    "onb.q.tools.hint": ("اختياري — تنجّم تعدّي.", "اختياري — يمكنك التخطي.", "Optionnel — vous pouvez passer.", "Optional — you can skip."),
    "onb.opt.student": ("طالب", "طالب", "Étudiant", "Student"),
    "onb.opt.employee": ("موظّف", "موظف", "Salarié", "Employee"),
    "onb.opt.freelance": ("حرّ", "مستقل", "Indépendant", "Freelancer"),
    "onb.opt.founder": ("صاحب مشروع", "صاحب مشروع", "Fondateur", "Founder"),
    "onb.opt.enterprise": ("مؤسسة", "مؤسسة", "Entreprise", "Enterprise"),
    "onb.opt.chat": ("محادثة", "محادثة", "Chat", "Chat"),
    "onb.opt.writing": ("كتابة", "كتابة", "Rédaction", "Writing"),
    "onb.opt.code": ("كود", "كود", "Code", "Code"),
    "onb.opt.devops": ("DevOps", "DevOps", "DevOps", "DevOps"),
    "onb.opt.data": ("تحليل بيانات", "تحليل بيانات", "Analyse de données", "Data analysis"),
    "onb.opt.marketing": ("تسويق", "تسويق", "Marketing", "Marketing"),
    "onb.opt.support": ("دعم عملاء", "دعم عملاء", "Support client", "Customer support"),
    "onb.opt.pm": ("إدارة مشاريع", "إدارة مشاريع", "Gestion de projet", "Project management"),
    "onb.opt.beginner": ("مبتدئ", "مبتدئ", "Débutant", "Beginner"),
    "onb.opt.intermediate": ("متوسّط", "متوسط", "Intermédiaire", "Intermediate"),
    "onb.opt.advanced": ("متقدّم", "متقدم", "Avancé", "Advanced"),
    "onb.opt.derja": ("دارجة تونسية", "دارجة تونسية", "Derja tunisien", "Tunisian Derja"),
    "onb.opt.fusha": ("عربي فصحى", "عربي فصحى", "Arabe standard", "Modern Standard Arabic"),
    "onb.opt.fr": ("Français", "Français", "Français", "French"),
    "onb.opt.en": ("English", "English", "English", "English"),
    "onb.opt.local": ("جهازي", "جهازي", "Ma machine", "This machine"),
    "onb.opt.server": ("سيرفر الشركة", "سيرفر الشركة", "Serveur d'entreprise", "Company server"),
    "onb.opt.offline": ("offline", "offline", "hors ligne", "offline"),
    "onb.opt.low": ("عادي", "منخفض", "Faible", "Low"),
    "onb.opt.medium": ("متوسّط", "متوسط", "Moyen", "Medium"),
    "onb.opt.high": ("عالٍ", "عالٍ", "Élevé", "High"),
    "onb.opt.files": ("ملفات", "ملفات", "Fichiers", "Files"),
    "onb.opt.shell_sandboxed": ("طرفية آمنة", "طرفية آمنة", "Terminal isolé", "Sandboxed shell"),
    "onb.opt.git": ("Git", "Git", "Git", "Git"),
    "onb.opt.rag": ("قاعدة معرفة", "قاعدة معرفة", "Base de connaissances", "Knowledge base"),
    "studio.title": ("🚀 Vibe Studio — من فكرة لتطبيق", "🚀 Vibe Studio — من فكرة إلى تطبيق", "🚀 Vibe Studio — de l'idée à l'app", "🚀 Vibe Studio — idea to app"),
    "studio.refresh": ("↻ تحديث", "↻ تحديث", "↻ Rafraîchir", "↻ Refresh"),
    "studio.back": ("رجوع للمنصّة", "رجوع للمنصة", "Retour à la plateforme", "Back to platform"),
    "studio.new": ("+ مشروع جديد", "+ مشروع جديد", "+ Nouveau projet", "+ New project"),
    "studio.empty": ("اختار مشروع ولا اعمل واحد جديد.", "اختر مشروعًا أو أنشئ واحدًا جديدًا.", "Choisissez un projet ou créez-en un.", "Pick a project or create one."),
    "studio.mission": ("▶ شغّل المهمة (PM → QA)", "▶ شغّل المهمة (PM → QA)", "▶ Lancer la mission (PM → QA)", "▶ Run mission (PM → QA)"),
    "studio.files": ("↻ الملفات", "↻ الملفات", "↻ Fichiers", "↻ Files"),
    "studio.zip": ("⬇ ZIP", "⬇ ZIP", "⬇ ZIP", "⬇ ZIP"),
    "studio.modal.title": ("مشروع جديد", "مشروع جديد", "Nouveau projet", "New project"),
    "studio.modal.hint": (
        "اكتب الفكرة بالدارجة، اختار القالب، وبدا.",
        "اكتب الفكرة، اختر القالب، وابدأ.",
        "Décrivez l'idée, choisissez le modèle, lancez.",
        "Describe the idea, pick a template, start.",
    ),
    "studio.field.name": ("الاسم", "الاسم", "Nom", "Name"),
    "studio.field.template": ("القالب", "القالب", "Modèle", "Template"),
    "studio.field.idea": ("الفكرة", "الفكرة", "Idée", "Idea"),
    "studio.create": ("اعمل المشروع", "أنشئ المشروع", "Créer le projet", "Create project"),
    "studio.no_projects": ("ما فمّاش مشاريع. اعمل واحد جديد.", "لا توجد مشاريع. أنشئ واحدًا.", "Aucun projet. Créez-en un.", "No projects yet. Create one."),
    "studio.running": ("جاري تشغيل المهمة: PM → Architect → Coder → QA …", "جارٍ تشغيل المهمة: PM → Architect → Coder → QA …", "Mission en cours : PM → Architect → Coder → QA …", "Mission running: PM → Architect → Coder → QA …"),
    "studio.created": ("المشروع تعمل ✓", "تم إنشاء المشروع ✓", "Projet créé ✓", "Project created ✓"),
    "studio.load_error": ("ما قدرناش نقراو المشاريع", "تعذّر قراءة المشاريع", "Impossible de lire les projets", "Could not load projects"),
    "studio.next": ("التالي", "التالي", "Ensuite", "Next"),
    "studio.tasks": ("مهام", "مهام", "tâches", "tasks"),
    "common.locale": ("اللغة", "اللغة", "Langue", "Language"),
}

for _key, (_tn, _ar, _fr, _en) in _UI_STRINGS.items():
    STRINGS[_key] = {"ar-TN": _tn, "ar": _ar, "fr": _fr, "en": _en}


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
