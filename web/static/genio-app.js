/* Genio OS — ربط الواجهة بـ API v9
   login/logout + onboarding (7 أسئلة) + Vibe Studio (projects + preview) */
(function () {
  "use strict";

  const CSRF_KEY = "genio_csrf";
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

  const $ = (id) => document.getElementById(id);

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
    const bootstrap = mode === "bootstrap";
    $("gioAuthTitle").textContent = bootstrap ? "أوّل حساب (المالك)" : "ادخل للمنصّة";
    $("gioAuthHint").textContent = bootstrap
      ? "ما فمّاش حتى حساب. اعمل حساب المالك الأوّل — بعدو المنصّة تولّي محمية بالجلسة."
      : "الإيميل وكلمة السر متاعك.";
    $("gioNameRow").hidden = !bootstrap;
    $("gioAuthSubmit").textContent = bootstrap ? "اعمل الحساب" : "ادخل";
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
        authError(res.data.error || "ما قدرناش ندخلو (" + res.status + ")");
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
      showAuth("login", "الجلسة ما تثبّتش — عاود ادخل.");
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
    out.textContent = "خروج";
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
      key: "occupation", title: "شنوّة تخدم؟", hint: "نختارو الشخصية والأدوات على أساسها.",
      type: "choice", options: [
        ["student", "طالب"], ["employee", "موظّف"], ["freelance", "حرّ"],
        ["founder", "صاحب مشروع"], ["enterprise", "مؤسسة"],
      ],
    },
    {
      key: "goals", title: "شنوّة تحب تعمل بالـ AI؟", hint: "تنجّم تختار أكثر من وحدة.",
      type: "multi", options: [
        ["chat", "محادثة"], ["writing", "كتابة"], ["code", "كود"], ["devops", "DevOps"],
        ["data", "تحليل بيانات"], ["marketing", "تسويق"], ["support", "دعم عملاء"], ["pm", "إدارة مشاريع"],
      ],
    },
    {
      key: "technical_level", title: "مستواك التقني؟", hint: "يحدّد صلاحيات الطرفية والـ sandbox.",
      type: "choice", options: [["beginner", "مبتدئ"], ["intermediate", "متوسّط"], ["advanced", "متقدّم"]],
    },
    {
      key: "register", title: "لغة الردود؟", hint: "", type: "choice",
      options: [["derja", "دارجة تونسية"], ["fusha", "عربي فصحى"], ["fr", "Français"], ["en", "English"]],
    },
    {
      key: "env", title: "وين يخدم الـ AI؟", hint: "محلي = بياناتك ما تخرجش.",
      type: "choice", options: [["local", "جهازي"], ["server", "سيرفر الشركة"], ["offline", "offline"]],
    },
    {
      key: "data_sensitivity", title: "عندك بيانات حسّاسة؟", hint: "عالٍ = الـ shell والشبكة يتقفلو.",
      type: "choice", options: [["low", "عادي"], ["medium", "متوسّط"], ["high", "عالٍ"]],
    },
    {
      key: "preferred_tools", title: "أهم أداة تحب تلقاها جاهزة؟", hint: "اختياري — تنجّم تعدّي.",
      type: "multi", optional: true, options: [
        ["files", "ملفات"], ["shell_sandboxed", "طرفية آمنة"], ["git", "Git"], ["rag", "قاعدة معرفة"],
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
    $("gioObTitle").textContent = step.title;
    const hint = $("gioObHint");
    hint.textContent = step.hint || "";
    hint.hidden = !step.hint;
    $("gioObCounter").textContent = (state.step + 1) + " / " + total;
    $("gioObBack").disabled = state.step === 0;
    $("gioObNext").textContent = state.step === total - 1 ? "كمّل ✓" : "التالي";

    const body = $("gioObBody");
    body.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "gio-choices";

    step.options.forEach(([value, label]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gio-choice";
      btn.textContent = label;
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
        toast(res.data.error || "ما قدرناش نسجّلو الاختيارات");
        return;
      }
      state.profile = res.data.profile;
      show("gioOnboarding", false);
      const persona = res.data.persona || {};
      toast("تمّ ✓ " + (persona.label || "الشخصية") + " — " + (persona.mode || ""));
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
      list.innerHTML = '<p class="gio-muted gio-small">' + (res.data.error || "ما قدرناش نقراو المشاريع") + "</p>";
      return;
    }
    state.projects = res.data.projects || [];
    if (state.projects.length === 0) {
      list.innerHTML = '<p class="gio-muted gio-small">ما فمّاش مشاريع. اعمل واحد جديد.</p>';
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
    if (!res.ok) { toast(res.data.error || "المشروع ما موجودش"); return; }
    state.current = res.data.project;
    $("gioProjectEmpty").hidden = true;
    $("gioProjectDetail").hidden = false;
    $("gioProjectName").textContent = state.current.name;
    $("gioProjectMeta").textContent =
      state.current.template + " • " + state.current.stack +
      (state.current.mobile ? " • mobile" : "") +
      " • " + (state.current.tasks || []).length + " مهام";
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
    log.textContent = "جاري تشغيل المهمة: PM → Architect → Coder → QA …";
    try {
      const res = await api("/api/projects/" + state.current.id + "/mission", {
        method: "POST",
        body: { idea: state.current.idea || "" },
      });
      if (!res.ok) {
        log.textContent = "خطأ: " + (res.data.error || res.status);
        return;
      }
      const lines = (res.data.tasks || []).map(
        (task) => "[" + task.stage + "] " + task.status + " — " + (task.artifact || "")
      );
      lines.push("");
      lines.push("التالي: " + (res.data.next || "—"));
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
        toast(res.data.error || "ما قدرناش نعملو المشروع");
        return;
      }
      show("gioNewProjectForm", false);
      $("gioNewName").value = "";
      $("gioNewIdea").value = "";
      await loadProjects();
      await selectProject(res.data.project.id);
      toast("المشروع تعمل ✓");
    } finally {
      submit.disabled = false;
    }
  }

  // ----------------------------------------------------------------------- boot
  async function boot() {
    // نوقّفو تحديث v8 القديم حتى نتأكدو من الجلسة
    window.__gioAuthed = false;

    const status = await api("/api/auth/status");
    if (!status.ok) {
      showAuth("login", "ما قدرناش نتواصلو مع الـ API.");
      return;
    }
    state.bootstrapped = !!status.data.bootstrapped;

    if (!status.data.authenticated) {
      showAuth(state.bootstrapped ? "login" : "bootstrap",
        state.bootstrapped ? "" : "الحساب الأوّل يولّي owner.");
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
})();
