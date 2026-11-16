/* Genio OS — ربط الواجهة بـ API v9
   login/logout + onboarding (7 أسئلة) + Vibe Studio (projects + preview)
   + i18n/RTL: كل نص من /api/i18n، والـ dir data ماشي تخمين */
(function () {
  "use strict";

  const CSRF_KEY = "genio_csrf";
  const LOCALE_KEY = "genio_locale";
  const FALLBACK_LOCALE = "ar-TN";

  const state = {
    user: null,
    csrf: null,
    bootstrapped: false,
    profile: null,
    step: 0,
    answers: {},
    projects: [],
    current: null,
  };

  // locale + catalogue: المصدر الوحيد للنصوص هو /api/i18n
  const i18n = {
    locale: FALLBACK_LOCALE,
    dir: "rtl",
    lang: "ar",
    strings: {},
    locales: [],
  };

  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------------ i18n
  function t(key, fallback) {
    const value = i18n.strings[key];
    return value === undefined || value === "" ? (fallback || key) : value;
  }

  function applyLocale() {
    const root = document.documentElement;
    root.setAttribute("dir", i18n.dir);
    root.setAttribute("lang", i18n.lang);

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"), el.textContent);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      el.setAttribute("placeholder", t(key, el.getAttribute("placeholder") || ""));
    });

    if (state.user) renderUserChip();
    const auth = $("gioAuth");
    if (auth && !auth.hidden) renderAuthTexts();
    const onboarding = $("gioOnboarding");
    if (onboarding && !onboarding.hidden) renderStep();
  }

  function renderAuthTexts() {
    const bootstrap = state.mode === "bootstrap";
    $("gioAuthTitle").textContent = bootstrap ? t("auth.title.bootstrap") : t("auth.title.login");
    $("gioAuthHint").textContent = bootstrap ? t("auth.hint.bootstrap") : t("auth.hint.login");
    $("gioAuthSubmit").textContent = bootstrap ? t("auth.create") : t("action.login");
    $("gioNameRow").hidden = !bootstrap;
  }

  async function setLocale(locale) {
    const res = await api("/api/i18n/" + encodeURIComponent(locale));
    if (!res.ok || !res.data.id) return false;
    i18n.locale = res.data.id;
    i18n.strings = res.data.strings || {};
    i18n.dir = res.data.dir || "rtl";
    i18n.lang = res.data.html_lang || "ar";
    try { localStorage.setItem(LOCALE_KEY, i18n.locale); } catch (e) {}
    applyLocale();
    renderLocaleSwitcher();
    return true;
  }

  function storedLocale() {
    try { return localStorage.getItem(LOCALE_KEY); } catch (e) { return null; }
  }

  async function loadI18n() {
    const list = await api("/api/i18n");
    if (list.ok) i18n.locales = list.data.locales || [];
    const wanted = storedLocale() || (list.ok ? list.data.default : FALLBACK_LOCALE);
    await setLocale(wanted || FALLBACK_LOCALE);
  }

  function renderLocaleSwitcher() {
    const hosts = [$("gioLocale"), $("gioLocaleStudio"), $("gioLocaleHeader")];
    hosts.forEach((host) => {
      if (!host) return;
      host.innerHTML = "";
      (i18n.locales.length ? i18n.locales : [{ id: FALLBACK_LOCALE, label: "دارجة" }]).forEach((item) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "gio-locale" + (item.id === i18n.locale ? " active" : "");
        btn.textContent = item.label;
        btn.title = item.id;
        btn.onclick = () => { setLocale(item.id); };
        host.appendChild(btn);
      });
      host.hidden = false;
    });
  }

  // ---------------------------------------------------------------- API helper
  function csrf() {
    if (!state.csrf) {
      try { state.csrf = localStorage.getItem(CSRF_KEY); } catch (e) {}
    }
    return state.csrf || "";
  }

  async function api(path, options) {
    const opts = Object.assign({ method: "GET" }, options || {});
    opts.headers = Object.assign({}, opts.headers || {});
    if (opts.body && typeof opts.body !== "string") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    if (opts.method !== "GET" && csrf()) {
      opts.headers["X-Genio-CSRF"] = csrf();
    }
    opts.credentials = "same-origin";
    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    return { ok: res.ok, status: res.status, data: data || {} };
  }

  function rememberSession(data) {
    if (data && data.csrf) {
      state.csrf = data.csrf;
      try { localStorage.setItem(CSRF_KEY, data.csrf); } catch (e) {}
    }
  }

  function toast(message) {
    const el = document.createElement("div");
    el.className = "gio-toast";
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  function show(id, visible) {
    const el = $(id);
    if (el) el.hidden = !visible;
  }

  // ------------------------------------------------------------------- auth UI
  function showAuth(mode, hint) {
    state.mode = mode;
    show("gioAuth", true);
    show("gioOnboarding", false);
    renderAuthTexts();
    $("gioAuthFoot").textContent = hint || "";
    $("gioAuthError").hidden = true;
    setTimeout(() => $("gioEmail").focus(), 50);
  }

  function authError(message) {
    const el = $("gioAuthError");
    el.textContent = message;
    el.hidden = false;
  }

  async function submitAuth(event) {
    event.preventDefault();
    const email = $("gioEmail").value.trim();
    const password = $("gioPassword").value;
    const displayName = $("gioName").value.trim();
    const path = state.mode === "bootstrap" ? "/api/auth/bootstrap" : "/api/auth/login";
    const body = state.mode === "bootstrap"
      ? { email: email, password: password, display_name: displayName }
      : { email: email, password: password };

    $("gioAuthSubmit").disabled = true;
    try {
      const res = await api(path, { method: "POST", body: body });
      if (!res.ok) {
        authError(res.data.error || "(" + res.status + ")");
        return;
      }
      rememberSession(res.data);
      state.user = res.data.user;
      $("gioPassword").value = "";
      await afterLogin();
    } finally {
      $("gioAuthSubmit").disabled = false;
    }
  }

  async function afterLogin() {
    show("gioAuth", false);
    const me = await api("/api/me");
    if (!me.ok) {
      showAuth("login", t("auth.hint.session"));
      return;
    }
    state.user = me.data.user;
    state.profile = me.data.profile;
    renderUserChip();
    window.__gioAuthed = true;
    if (me.data.profile && Number(me.data.profile.onboarding_done) === 0) {
      startOnboarding();
    } else {
      finishBoot();
    }
  }

  function renderUserChip() {
    const host = $("gioUserChip");
    if (!host || !state.user) return;
    host.innerHTML = "";
    const chip = document.createElement("span");
    chip.className = "gio-user-chip";
    chip.id = "gioUserChipInner";
    const who = document.createElement("span");
    who.textContent = "👤 " + (state.user.display_name || state.user.email);
    const role = document.createElement("span");
    role.style.opacity = ".7";
    role.textContent = state.user.role;
    const out = document.createElement("button");
    out.textContent = t("action.logout");
    out.onclick = logout;
    chip.append(who, role, out);
    host.appendChild(chip);
    host.hidden = false;
  }

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    state.user = null;
    state.csrf = null;
    window.__gioAuthed = false;
    try { localStorage.removeItem(CSRF_KEY); } catch (e) {}
    show("gioStudio", false);
    const chip = $("gioUserChip");
    if (chip) chip.hidden = true;
    showAuth("login");
  }

  // ------------------------------------------------------------- onboarding UI
  const STEPS = [
    {
      key: "occupation", titleKey: "onb.q.occupation.title", hintKey: "onb.q.occupation.hint",
      type: "choice", options: [
        ["student", "onb.opt.student"], ["employee", "onb.opt.employee"], ["freelance", "onb.opt.freelance"],
        ["founder", "onb.opt.founder"], ["enterprise", "onb.opt.enterprise"],
      ],
    },
    {
      key: "goals", titleKey: "onb.q.goals.title", hintKey: "onb.q.goals.hint",
      type: "multi", options: [
        ["chat", "onb.opt.chat"], ["writing", "onb.opt.writing"], ["code", "onb.opt.code"], ["devops", "onb.opt.devops"],
        ["data", "onb.opt.data"], ["marketing", "onb.opt.marketing"], ["support", "onb.opt.support"], ["pm", "onb.opt.pm"],
      ],
    },
    {
      key: "technical_level", titleKey: "onb.q.level.title", hintKey: "onb.q.level.hint",
      type: "choice", options: [["beginner", "onb.opt.beginner"], ["intermediate", "onb.opt.intermediate"], ["advanced", "onb.opt.advanced"]],
    },
    {
      key: "register", titleKey: "onb.q.register.title", hintKey: "onb.q.register.hint", type: "choice",
      options: [["derja", "onb.opt.derja"], ["fusha", "onb.opt.fusha"], ["fr", "onb.opt.fr"], ["en", "onb.opt.en"]],
    },
    {
      key: "env", titleKey: "onb.q.env.title", hintKey: "onb.q.env.hint", type: "choice",
      options: [["local", "onb.opt.local"], ["server", "onb.opt.server"], ["offline", "onb.opt.offline"]],
    },
    {
      key: "data_sensitivity", titleKey: "onb.q.sensitivity.title", hintKey: "onb.q.sensitivity.hint", type: "choice",
      options: [["low", "onb.opt.low"], ["medium", "onb.opt.medium"], ["high", "onb.opt.high"]],
    },
    {
      key: "preferred_tools", titleKey: "onb.q.tools.title", hintKey: "onb.q.tools.hint",
      type: "multi", optional: true, options: [
        ["files", "onb.opt.files"], ["shell_sandboxed", "onb.opt.shell_sandboxed"], ["git", "onb.opt.git"], ["rag", "onb.opt.rag"],
      ],
    },
  ];

  function defaults() {
    return {
      occupation: "employee", goals: ["chat"], technical_level: "intermediate",
      register: "derja", env: "local", data_sensitivity: "medium", preferred_tools: [],
    };
  }

  function startOnboarding() {
    state.step = 0;
    state.answers = defaults();
    show("gioOnboarding", true);
    renderStep();
  }

  function renderStep() {
    const step = STEPS[state.step];
    const total = STEPS.length;
    $("gioProgressBar").style.width = Math.round(((state.step + 1) / total) * 100) + "%";
    $("gioObTitle").textContent = t(step.titleKey);
    const hintText = t(step.hintKey, "");
    const hint = $("gioObHint");
    hint.textContent = hintText;
    hint.hidden = !hintText;
    $("gioObCounter").textContent = (state.step + 1) + " / " + total;
    $("gioObBack").disabled = state.step === 0;
    $("gioObBack").textContent = t("onb.back");
    $("gioObNext").textContent = state.step === total - 1 ? t("onb.finish") : t("onb.next");
    $("gioObSkip").textContent = t("onboarding.skip");

    const body = $("gioObBody");
    body.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "gio-choices";

    step.options.forEach(([value, labelKey]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gio-choice";
      btn.dataset.value = value;
      btn.textContent = t(labelKey, value);
      const current = state.answers[step.key];
      const selected = step.type === "multi"
        ? Array.isArray(current) && current.indexOf(value) >= 0
        : current === value;
      if (selected) btn.classList.add("selected");
      btn.onclick = () => {
        if (step.type === "multi") {
          const list = Array.isArray(state.answers[step.key]) ? state.answers[step.key].slice() : [];
          const at = list.indexOf(value);
          if (at >= 0) list.splice(at, 1); else list.push(value);
          state.answers[step.key] = list;
        } else {
          state.answers[step.key] = value;
        }
        renderStep();
      };
      wrap.appendChild(btn);
    });
    body.appendChild(wrap);
  }

  function nextStep() {
    if (state.step < STEPS.length - 1) {
      state.step += 1;
      renderStep();
    } else {
      submitOnboarding();
    }
  }

  function prevStep() {
    if (state.step > 0) {
      state.step -= 1;
      renderStep();
    }
  }

  async function submitOnboarding() {
    const payload = Object.assign(defaults(), state.answers);
    if (!payload.goals || payload.goals.length === 0) payload.goals = ["chat"];
    $("gioObNext").disabled = true;
    try {
      const res = await api("/api/onboarding/submit", { method: "POST", body: payload });
      if (!res.ok) {
        toast(res.data.error || t("status.error"));
        return;
      }
      state.profile = res.data.profile;
      show("gioOnboarding", false);
      const persona = res.data.persona || {};
      toast("✓ " + (persona.label || t("status.ready")) + " — " + (persona.mode || ""));
      finishBoot();
    } finally {
      $("gioObNext").disabled = false;
    }
  }

  // -------------------------------------------------------------- Vibe Studio
  async function openStudio() {
    show("gioStudio", true);
    await loadTemplates();
    await loadProjects();
  }

  async function loadTemplates() {
    const res = await api("/api/projects/templates");
    const select = $("gioTemplate");
    if (!res.ok || !select) return;
    select.innerHTML = "";
    res.data.templates.forEach((tpl) => {
      const option = document.createElement("option");
      option.value = tpl.id;
      option.textContent = tpl.label + (tpl.mobile ? " (mobile)" : "");
      select.appendChild(option);
    });
  }

  async function loadProjects() {
    const res = await api("/api/projects");
    const list = $("gioProjectList");
    list.innerHTML = "";
    if (!res.ok) {
      list.innerHTML = '<p class="gio-muted gio-small">' + (res.data.error || t("studio.load_error")) + "</p>";
      return;
    }
    state.projects = res.data.projects || [];
    if (state.projects.length === 0) {
      list.innerHTML = '<p class="gio-muted gio-small">' + t("studio.no_projects") + "</p>";
      return;
    }
    state.projects.forEach((project) => {
      const item = document.createElement("button");
      item.className = "gio-list-item" + (state.current && state.current.id === project.id ? " active" : "");
      item.innerHTML = "<strong></strong><small></small>";
      item.querySelector("strong").textContent = project.name;
      item.querySelector("small").textContent = project.template + " • " + project.stack;
      item.onclick = () => selectProject(project.id);
      list.appendChild(item);
    });
  }

  async function selectProject(id) {
    const res = await api("/api/projects/" + id);
    if (!res.ok) { toast(res.data.error || t("status.error")); return; }
    state.current = res.data.project;
    $("gioProjectEmpty").hidden = true;
    $("gioProjectDetail").hidden = false;
    $("gioProjectName").textContent = state.current.name;
    $("gioProjectMeta").textContent =
      state.current.template + " • " + state.current.stack +
      (state.current.mobile ? " • mobile" : "") +
      " • " + (state.current.tasks || []).length + " " + t("studio.tasks");
    $("gioMissionLog").hidden = true;
    await loadFiles();
    $("gioPreview").src = "/api/projects/" + id + "/preview?" + Date.now();
    await loadProjects();
  }

  async function loadFiles() {
    if (!state.current) return;
    const res = await api("/api/projects/" + state.current.id + "/files");
    const box = $("gioFileList");
    box.innerHTML = "";
    if (!res.ok) return;
    res.data.files.forEach((file, index) => {
      const btn = document.createElement("button");
      btn.className = "gio-file" + (index === 0 ? " active" : "");
      btn.textContent = file.path;
      btn.onclick = async () => {
        box.querySelectorAll(".gio-file").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const fileRes = await api(
          "/api/projects/" + state.current.id + "/file?path=" + encodeURIComponent(file.path)
        );
        if (fileRes.ok) {
          $("gioPreview").srcdoc =
            '<pre style="direction:ltr;text-align:left;padding:12px;font:12px ui-monospace">' +
            fileRes.data.content.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</pre>";
        }
      };
      box.appendChild(btn);
    });
  }

  async function runMission() {
    if (!state.current) return;
    const button = $("gioRunMission");
    button.disabled = true;
    const log = $("gioMissionLog");
    log.hidden = false;
    log.textContent = t("studio.running");
    try {
      const res = await api("/api/projects/" + state.current.id + "/mission", {
        method: "POST",
        body: { idea: state.current.idea || "" },
      });
      if (!res.ok) {
        log.textContent = t("status.error") + ": " + (res.data.error || res.status);
        return;
      }
      const lines = (res.data.tasks || []).map(
        (task) => "[" + task.stage + "] " + task.status + " — " + (task.artifact || "")
      );
      lines.push("");
      lines.push(t("studio.next") + ": " + (res.data.next || "—"));
      log.textContent = lines.join("\n");
      await selectProject(state.current.id);
    } finally {
      button.disabled = false;
    }
  }

  async function createProject(event) {
    event.preventDefault();
    const name = $("gioNewName").value.trim();
    const template = $("gioTemplate").value;
    const idea = $("gioNewIdea").value.trim();
    const submit = $("gioCreateSubmit");
    submit.disabled = true;
    try {
      const res = await api("/api/projects", {
        method: "POST",
        body: { name: name, template: template, idea: idea },
      });
      if (!res.ok) {
        toast(res.data.error || t("status.error"));
        return;
      }
      show("gioNewProjectForm", false);
      $("gioNewName").value = "";
      $("gioNewIdea").value = "";
      await loadProjects();
      await selectProject(res.data.project.id);
      toast(t("studio.created"));
    } finally {
      submit.disabled = false;
    }
  }

  // ----------------------------------------------------------------------- boot
  async function boot() {
    // نوقّفو تحديث v8 القديم حتى نتأكدو من الجلسة
    window.__gioAuthed = false;

    await loadI18n();

    const status = await api("/api/auth/status");
    if (!status.ok) {
      showAuth("login", t("auth.hint.no_api"));
      return;
    }
    state.bootstrapped = !!status.data.bootstrapped;

    // لغة الحساب تخدم كان ما فمّاش اختيار محفوظ في المتصفّح
    const profileLocale = status.data.profile && status.data.profile.locale;
    if (!storedLocale() && profileLocale && profileLocale !== i18n.locale) {
      await setLocale(profileLocale);
    }

    if (!status.data.authenticated) {
      showAuth(state.bootstrapped ? "login" : "bootstrap",
        state.bootstrapped ? "" : t("auth.hint.owner"));
      return;
    }

    state.user = status.data.user;
    state.profile = status.data.profile;
    window.__gioAuthed = true;
    renderUserChip();
    if (status.data.profile && Number(status.data.profile.onboarding_done) === 0) {
      startOnboarding();
    } else {
      finishBoot();
    }
  }

  function finishBoot() {
    show("gioAuth", false);
    show("gioOnboarding", false);
    renderUserChip();
    if (typeof window.refreshAll === "function") {
      try { window.refreshAll(); } catch (e) {}
    }
  }

  // --------------------------------------------------------------- wiring
  document.addEventListener("DOMContentLoaded", () => {
    const form = $("gioAuthForm");
    if (form) form.addEventListener("submit", submitAuth);

    const bind = (id, handler) => {
      const el = $(id);
      if (el) el.addEventListener("click", handler);
    };

    bind("gioObNext", nextStep);
    bind("gioObBack", prevStep);
    bind("gioObSkip", submitOnboarding);
    bind("gioOpenStudio", openStudio);
    bind("gioStudioClose", () => show("gioStudio", false));
    bind("gioStudioLogout", logout);
    bind("gioNewProject", () => show("gioNewProjectForm", true));
    bind("gioNewCancel", () => show("gioNewProjectForm", false));
    bind("gioRunMission", runMission);
    bind("gioRefreshFiles", loadFiles);
    bind("gioPanelRefresh", loadProjects);

    const newForm = $("gioNewProjectForm2");
    if (newForm) newForm.addEventListener("submit", createProject);

    const exportLink = $("gioExport");
    if (exportLink) {
      exportLink.addEventListener("click", (event) => {
        if (!state.current) return;
        event.preventDefault();
        window.location.href = "/api/projects/" + state.current.id + "/export";
      });
    }

    boot();
  });

  // للتجربة/التصحيح: الواجهة تعرض حالتها، والاختبارات تقراها
  window.__gioI18n = i18n;
  window.__gioSetLocale = setLocale;
})();
