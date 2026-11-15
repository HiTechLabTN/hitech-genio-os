from pathlib import Path

index_path = Path("/data/genio-os/web/static/index.html")
html = index_path.read_text(encoding="utf-8")

# تحديث محرك الحركة والحالات في Three.js ليدعم المسارات وفقاعات الحالة
old_block_start = "function setAgentVisualState(agentId, state) {"
old_block_end = "async function streamAgentTask(agentId, rawPrompt) {"

new_walk_engine = r'''
function updateStatusBubble(av, text, borderColor = "#00f2fe") {
  if (av.bubble) {
    av.mesh.remove(av.bubble);
    av.bubble.material.map.dispose();
    av.bubble.material.dispose();
  }
  if (!text) return;
  const canvas = document.createElement("canvas");
  canvas.width = 512; canvas.height = 110;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(2, 6, 23, 0.92)";
  ctx.strokeStyle = borderColor;
  ctx.lineWidth = 6;
  ctx.strokeRect(8, 8, 496, 94);
  ctx.fillRect(8, 8, 496, 94);
  ctx.font = "bold 30px Segoe UI, sans-serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 256, 55);
  const tex = new THREE.CanvasTexture(canvas);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: tex, transparent: true}));
  sp.scale.set(3.2, 0.7, 1);
  sp.position.set(0, 2.55, 0);
  av.mesh.add(sp);
  av.bubble = sp;
}

function setAgentVisualState(agentId, state, customBubble = "") {
  const av = avatarMap[agentId];
  if(!av) return;
  av.state = state;

  // تحديث النقطة المضيئة في القائمة الجانبية
  const cards = document.querySelectorAll(".agent-card");
  cards.forEach(c => {
    if(c.innerText.includes(agentId)) {
      const dot = c.querySelector(".status-dot");
      if(dot) {
        if(state === "working") { dot.style.background = "#f59e0b"; dot.style.boxShadow = "0 0 10px #f59e0b"; }
        else if(state === "walking" || state === "reporting") { dot.style.background = "#00f2fe"; dot.style.boxShadow = "0 0 10px #00f2fe"; }
        else { dot.style.background = "#10b981"; dot.style.boxShadow = "0 0 8px #10b981"; }
      }
    }
  });

  if(state === "working") {
    av.lamp.material.color.setHex(0xf59e0b);
    av.lamp.material.emissive.setHex(0xf59e0b);
    av.lamp.material.emissiveIntensity = 2.2;
    updateStatusBubble(av, customBubble || "⚡ يشتغل عالمهمة...", "#f59e0b");
  } else if(state === "walking") {
    av.lamp.material.color.setHex(0x00f2fe);
    av.lamp.material.emissive.setHex(0x00f2fe);
    av.lamp.material.emissiveIntensity = 1.6;
    updateStatusBubble(av, customBubble || "🚶‍♂️ في الطريق للـ CEO...", "#00f2fe");
  } else if(state === "reporting") {
    av.lamp.material.color.setHex(0xa855f7);
    av.lamp.material.emissive.setHex(0xa855f7);
    av.lamp.material.emissiveIntensity = 2.0;
    updateStatusBubble(av, customBubble || "📋 يسلم التقرير للـ CEO!", "#a855f7");
  } else {
    av.lamp.material.color.setHex(0x10b981);
    av.lamp.material.emissive.setHex(0x10b981);
    av.lamp.material.emissiveIntensity = 0.9;
    updateStatusBubble(av, customBubble || "🟢 جاهز بالمكتب", "#10b981");
  }
}

function demoWalkToCEO(agentId = "Dev-Lead") {
  const av = avatarMap[agentId];
  const ceo = avatarMap["Genio-Rayes"];
  if(!av || !ceo || agentId === "Genio-Rayes") return;

  setAgentVisualState(agentId, "walking", "📄 يحمل التقرير للـ CEO");
  setAgentVisualState("Genio-Rayes", "working", "📞 يستقبل تقرير القسم...");
  document.getElementById("hqStatusText").innerText = `🚶‍♂️ ${agentId} خرج من مكتبه ويتحرك عبر الممر الرئيسي نحو مكتب المدير التنفيذي...`;

  // مسار المشي عبر الممر المركزي (Waypoints) لتفادي اختراق الجدران
  av.waypoints = [
    {x: 0, z: av.homeZ},                 // 1. الخروج إلى الممر الوسطي
    {x: 0, z: ceo.homeZ + 1.9},          // 2. التقدم في الممر حتى مكتب الـ CEO
    {
      x: 0, z: ceo.homeZ + 1.9,
      pause: 140,                        // 3. الوقوف لتسليم التقرير ومناقشته
      onReach: () => {
        setAgentVisualState(agentId, "reporting", "✅ تم التسليم بنجاح!");
        setAgentVisualState("Genio-Rayes", "reporting", "👑 أحسنت! تم الاعتماد");
        document.getElementById("hqStatusText").innerText = `🤝 ${agentId} يسلّم التقرير الآن للمدير التنفيذي (Genio-Rayes)...`;
      }
    },
    {
      x: 0, z: av.homeZ,                 // 4. الرجوع عبر الممر الوسطي
      onStart: () => {
        setAgentVisualState(agentId, "walking", "🔙 عائد إلى المكتب...");
        setAgentVisualState("Genio-Rayes", "idle", "👑 يراجع لوحة الشركة");
        document.getElementById("hqStatusText").innerText = `🔙 ${agentId} أنهى التسليم ويعود الآن إلى مكتبه...`;
      }
    },
    {
      x: av.homeX, z: av.homeZ,          // 5. الدخول للمكتب والجلوس
      onReach: () => {
        setAgentVisualState(agentId, "idle", "🟢 فاضي ومستعد");
        document.getElementById("hqStatusText").innerText = `✅ ${agentId} عاد إلى مكتبه واللمبة خضراء (جاهز للمهمة القادمة).`;
      }
    }
  ];
}

function animate3D() {
  requestAnimationFrame(animate3D);
  const t = Date.now() * 0.006;

  Object.values(avatarMap).forEach(av => {
    const parts = av.mesh.userData;

    if (av.waypoints && av.waypoints.length > 0) {
      const wp = av.waypoints[0];
      if (wp.onStart && !wp.started) {
        wp.started = true;
        wp.onStart();
      }
      const dx = wp.x - av.mesh.position.x;
      const dz = wp.z - av.mesh.position.z;
      const dist = Math.hypot(dx, dz);

      if (dist > 0.12) {
        const speed = 0.09;
        av.mesh.position.x += (dx / dist) * speed;
        av.mesh.position.z += (dz / dist) * speed;
        av.mesh.rotation.y = Math.atan2(-dx, -dz);

        // أنيميشن المشي (تحريك الأرجل واليدين واهتزاز خفيف للجسم)
        parts.leftLeg.rotation.x = Math.sin(t * 3.2) * 0.75;
        parts.rightLeg.rotation.x = -Math.sin(t * 3.2) * 0.75;
        parts.leftArm.rotation.x = -Math.sin(t * 3.2) * 0.65;
        parts.rightArm.rotation.x = Math.sin(t * 3.2) * 0.65;
        av.mesh.position.y = 0.08 + Math.abs(Math.sin(t * 3.2)) * 0.08;
      } else {
        av.mesh.position.y = 0.08;
        parts.leftLeg.rotation.x = 0;
        parts.rightLeg.rotation.x = 0;

        if (wp.onReach && !wp.reached) {
          wp.reached = true;
          wp.onReach();
        }
        if (wp.pause && wp.pause > 0) {
          wp.pause--;
          // حركة نقاش وتفاعل أمام مكتب المدير
          av.mesh.rotation.y = 0;
          parts.leftArm.rotation.x = -0.5 + Math.sin(t * 4) * 0.3;
          parts.rightArm.rotation.x = -0.5 - Math.sin(t * 4) * 0.3;
          parts.head.rotation.x = Math.sin(t * 3) * 0.15;
        } else {
          av.waypoints.shift();
        }
      }
    } else {
      av.mesh.rotation.y = 0;
      av.mesh.position.y = 0.08;
      parts.leftLeg.rotation.x = 0;
      parts.rightLeg.rotation.x = 0;
      parts.head.rotation.x = 0;

      if(av.state === "working") {
        // أنيميشن الكتابة السريعة على الكيبورد وتوهج الشاشة
        parts.leftArm.rotation.x = -0.8 + Math.sin(t * 6) * 0.28;
        parts.rightArm.rotation.x = -0.8 - Math.sin(t * 6) * 0.28;
        parts.head.rotation.y = Math.sin(t * 2.5) * 0.2;
        av.monitor.material.emissiveIntensity = 1.1 + Math.sin(t * 7) * 0.45;
      } else {
        // تنفس هادئ وحركة انتظار طبيعية
        parts.leftArm.rotation.x = Math.sin(t * 0.5 + av.phase) * 0.07;
        parts.rightArm.rotation.x = -Math.sin(t * 0.5 + av.phase) * 0.07;
        parts.head.rotation.y = Math.sin(t * 0.4 + av.phase) * 0.12;
        av.monitor.material.emissiveIntensity = 0.65;
      }
    }
  });

  if(renderer && scene && camera) renderer.render(scene, camera);
}
'''

if old_block_start in html and old_block_end in html:
    pre = html.split(old_block_start)[0]
    post = html.split(old_block_end)[1]
    updated_html = pre + new_walk_engine + "\n" + old_block_end + post
    # تهيئة فقاعات الحالة الابتدائية عند تشغيل المكتب
    updated_html = updated_html.replace(
        "window.addEventListener(\"resize\", onResize3D);",
        "window.addEventListener(\"resize\", onResize3D);\n  Object.keys(avatarMap).forEach(id => setAgentVisualState(id, 'idle', '🟢 في المكتب'));"
    )
    index_path.write_text(updated_html, encoding="utf-8")
    print("✅ تم تفعيل نظام المشي عبر الممرات، فقاعات الحوار، وتحديث حالات اللمبات بنجاح!")
else:
    print("⚠️ لم يتم العثور على البلوك المستهدف، تأكد من وجود نسخة v7.0.")
