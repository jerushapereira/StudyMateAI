const state = {
  user: null,
  profile: {},
  roadmapData: null,
  progress: {},
  chart: null,
};

const elements = {
  form: document.querySelector("#profileForm"),
  submitButton: document.querySelector(".profile-panel .primary-button"),
  submitText: document.querySelector("#submitText"),
  formError: document.querySelector("#formError"),
  roadmapList: document.querySelector("#roadmapList"),
  emptyRoadmap: document.querySelector("#emptyRoadmap"),
  gapList: document.querySelector("#gapList"),
  weekList: document.querySelector("#weekList"),
  projectGrid: document.querySelector("#projectGrid"),
  progressValue: document.querySelector("#progressValue"),
  progressFill: document.querySelector("#progressFill"),
  progressHint: document.querySelector("#progressHint"),
  roadmapStatus: document.querySelector("#roadmapStatus"),
  timelineStat: document.querySelector("#timelineStat"),
  phaseStat: document.querySelector("#phaseStat"),
  gapStat: document.querySelector("#gapStat"),
  resetProgress: document.querySelector("#resetProgress"),
  reanalyzeBtn: document.querySelector("#reanalyzeBtn"),
  chatForm: document.querySelector("#chatForm"),
  chatInput: document.querySelector("#chatInput"),
  chatWindow: document.querySelector("#chatWindow"),
  themeToggle: document.querySelector("#themeToggle"),
  themeLabel: document.querySelector("#themeLabel"),
  toast: document.querySelector("#toast"),
  authLoggedOut: document.querySelector("#authLoggedOut"),
  authLoggedIn: document.querySelector("#authLoggedIn"),
  showLogin: document.querySelector("#showLogin"),
  showRegister: document.querySelector("#showRegister"),
  loginForm: document.querySelector("#loginForm"),
  registerForm: document.querySelector("#registerForm"),
  authError: document.querySelector("#authError"),
  accountAvatar: document.querySelector("#accountAvatar"),
  accountName: document.querySelector("#accountName"),
  accountEmail: document.querySelector("#accountEmail"),
  logoutButton: document.querySelector("#logoutButton"),
};

document.addEventListener("DOMContentLoaded", async () => {
  restoreTheme();
  await initAuth();
  restoreSavedRoadmap();
  initChart();
});

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.formError.textContent = "";
  state.profile = readProfile();

  if (!state.profile.skills || !state.profile.targetRole) {
    elements.formError.textContent = "Please add your skills and target role.";
    return;
  }

  setLoading(true, "Generating...");
  try {
    const data = await postJson("/generate-roadmap", state.profile);
    state.roadmapData = normalizeRoadmap(data);
    state.progress = loadProgress(state.roadmapData);
    persistRoadmap();
    renderAll();
    showToast("Your personalized roadmap is ready.");
  } catch (error) {
    elements.formError.textContent = error.message;
  } finally {
    setLoading(false, "Generate roadmap");
  }
});

elements.reanalyzeBtn.addEventListener("click", async () => {
  const profile = state.profile.targetRole ? state.profile : readProfile();
  if (!profile.skills || !profile.targetRole) {
    showToast("Generate a roadmap or fill the profile first.");
    return;
  }

  elements.reanalyzeBtn.disabled = true;
  elements.reanalyzeBtn.textContent = "Analyzing...";
  try {
    const data = await postJson("/analyze-skills", profile);
    const gaps = data.skillGaps || [];
    if (!state.roadmapData) {
      state.roadmapData = { roadmap: [], weeklyPlan: [], skillGaps: gaps, targetRole: profile.targetRole };
    } else {
      state.roadmapData.skillGaps = gaps;
    }
    persistRoadmap();
    renderSkillGaps();
    updateStats();
    showToast("Skill gaps refreshed.");
  } catch (error) {
    showToast(error.message);
  } finally {
    elements.reanalyzeBtn.disabled = false;
    elements.reanalyzeBtn.textContent = "Re-analyze";
  }
});

elements.resetProgress.addEventListener("click", () => {
  if (!state.roadmapData) return;
  state.progress = {};
  saveProgress();
  renderRoadmap();
  updateProgress();
  showToast("Progress reset.");
});

elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = elements.chatInput.value.trim();
  if (!message) return;

  appendChat("user", message);
  elements.chatInput.value = "";
  const typing = appendChat("bot", "Thinking...");

  try {
    const data = await postJson("/chat", {
      message,
      profile: state.profile,
      roadmapContext: state.roadmapData || {},
    });
    typing.textContent = data.reply || "I could not generate a response this time.";
  } catch (error) {
    typing.textContent = error.message;
  }
  elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
});

elements.themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  localStorage.setItem("careerTheme", document.body.classList.contains("dark") ? "dark" : "light");
  updateThemeLabel();
  updateProgress();
});

elements.showLogin.addEventListener("click", () => setAuthMode("login"));
elements.showRegister.addEventListener("click", () => setAuthMode("register"));

elements.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.authError.textContent = "";
  try {
    const data = await postJson("/auth/login", {
      email: document.querySelector("#loginEmail").value.trim(),
      password: document.querySelector("#loginPassword").value,
    });
    setCurrentUser(data.user);
    showToast("Logged in successfully.");
  } catch (error) {
    elements.authError.textContent = error.message;
  }
});

elements.registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.authError.textContent = "";
  try {
    const data = await postJson("/auth/register", {
      name: document.querySelector("#registerName").value.trim(),
      email: document.querySelector("#registerEmail").value.trim(),
      password: document.querySelector("#registerPassword").value,
    });
    setCurrentUser(data.user);
    document.querySelector("#name").value = data.user.name;
    state.profile.name = data.user.name;
    showToast("Account created. You are logged in.");
  } catch (error) {
    elements.authError.textContent = error.message;
  }
});

elements.logoutButton.addEventListener("click", async () => {
  await postJson("/auth/logout", {});
  setCurrentUser(null);
  showToast("Logged out.");
});

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed. Please try again.");
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url, { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed. Please try again.");
  }
  return data;
}

async function initAuth() {
  try {
    const data = await getJson("/auth/me");
    setCurrentUser(data.user || null, false);
  } catch {
    setCurrentUser(null, false);
  }
}

function setAuthMode(mode) {
  const isLogin = mode === "login";
  elements.showLogin.classList.toggle("active", isLogin);
  elements.showRegister.classList.toggle("active", !isLogin);
  elements.loginForm.classList.toggle("hidden", !isLogin);
  elements.registerForm.classList.toggle("hidden", isLogin);
  elements.authError.textContent = "";
}

function setCurrentUser(user, shouldRestore = true) {
  state.user = user;
  elements.authLoggedOut.classList.toggle("hidden", Boolean(user));
  elements.authLoggedIn.classList.toggle("hidden", !user);

  if (user) {
    elements.accountAvatar.textContent = user.name.slice(0, 1).toUpperCase();
    elements.accountName.textContent = user.name;
    elements.accountEmail.textContent = user.email;
  }

  if (shouldRestore) {
    restoreSavedRoadmap();
    updateProgress();
  }
}

function readProfile() {
  return {
    name: document.querySelector("#name").value.trim(),
    skills: document.querySelector("#skills").value.trim(),
    experienceLevel: document.querySelector("#experienceLevel").value,
    targetRole: document.querySelector("#targetRole").value.trim(),
  };
}

function normalizeRoadmap(data) {
  return {
    profileSummary: data.profileSummary || "",
    targetRole: data.targetRole || state.profile.targetRole || "Target role",
    estimatedTimeline: data.estimatedTimeline || "Timeline pending",
    roadmap: Array.isArray(data.roadmap) ? data.roadmap : [],
    skillGaps: Array.isArray(data.skillGaps) ? data.skillGaps : [],
    weeklyPlan: Array.isArray(data.weeklyPlan) ? data.weeklyPlan : [],
    portfolioTips: Array.isArray(data.portfolioTips) ? data.portfolioTips : [],
  };
}

function renderAll() {
  renderRoadmap();
  renderSkillGaps();
  renderWeeklyPlan();
  renderProjects();
  updateStats();
  updateProgress();
}

function renderRoadmap() {
  elements.roadmapList.innerHTML = "";
  const phases = state.roadmapData?.roadmap || [];
  elements.emptyRoadmap.style.display = phases.length ? "none" : "block";
  elements.roadmapStatus.textContent = phases.length ? "Generated" : "Waiting for input";

  phases.forEach((phase, phaseIndex) => {
    const card = document.createElement("article");
    card.className = "phase-card";
    const topics = Array.isArray(phase.topics) ? phase.topics : [];
    card.innerHTML = `
      <div class="phase-top">
        <div>
          <h4>${escapeHtml(phase.title || `Phase ${phaseIndex + 1}`)}</h4>
          <p class="phase-meta">${escapeHtml(phase.duration || "Flexible")} | ${escapeHtml(phase.goal || "")}</p>
        </div>
        <span class="tag">${escapeHtml(phase.milestone || "Milestone")}</span>
      </div>
      <div class="topic-list"></div>
    `;

    const topicList = card.querySelector(".topic-list");
    topics.forEach((topic, topicIndex) => {
      const id = getTopicId(phase, phaseIndex, topic, topicIndex);
      const row = document.createElement("label");
      row.className = "check-row";
      row.innerHTML = `
        <span>${escapeHtml(topic)}</span>
        <input type="checkbox" ${state.progress[id] ? "checked" : ""} aria-label="Mark ${escapeHtml(topic)} complete" />
      `;
      row.querySelector("input").addEventListener("change", (event) => {
        state.progress[id] = event.target.checked;
        saveProgress();
        updateProgress();
      });
      topicList.appendChild(row);
    });

    elements.roadmapList.appendChild(card);
  });
}

function renderSkillGaps() {
  elements.gapList.innerHTML = "";
  const gaps = state.roadmapData?.skillGaps || [];
  if (!gaps.length) {
    elements.gapList.innerHTML = `<div class="empty-state">Skill gaps will appear after generation.</div>`;
    return;
  }

  gaps.forEach((gap) => {
    const isMust = (gap.priority || "").toLowerCase().includes("must");
    const card = document.createElement("article");
    card.className = "gap-card";
    card.innerHTML = `
      <span class="priority tag ${isMust ? "must" : ""}">${escapeHtml(gap.priority || "Optional")}</span>
      <h4>${escapeHtml(gap.skill || "Skill")}</h4>
      <p>${escapeHtml(gap.reason || "")}</p>
      <p><strong>Action:</strong> ${escapeHtml(gap.suggestedAction || "Practice this in your next project.")}</p>
    `;
    elements.gapList.appendChild(card);
  });
}

function renderWeeklyPlan() {
  elements.weekList.innerHTML = "";
  const weeks = state.roadmapData?.weeklyPlan || [];
  if (!weeks.length) {
    elements.weekList.innerHTML = `<div class="empty-state">A weekly schedule will appear here.</div>`;
    return;
  }

  weeks.forEach((week) => {
    const tasks = Array.isArray(week.tasks) ? week.tasks.join(", ") : "";
    const card = document.createElement("article");
    card.className = "week-card";
    card.innerHTML = `
      <h4>${escapeHtml(week.week || "Week")}: ${escapeHtml(week.focus || "Focus")}</h4>
      <p>${escapeHtml(tasks)}</p>
      <span class="tag">${escapeHtml(week.deliverable || "Deliverable")}</span>
    `;
    elements.weekList.appendChild(card);
  });
}

function renderProjects() {
  elements.projectGrid.innerHTML = "";
  const projects = (state.roadmapData?.roadmap || []).flatMap((phase) =>
    (phase.projects || []).map((project) => ({ ...project, phase: phase.title }))
  );

  if (!projects.length) {
    elements.projectGrid.innerHTML = `<div class="empty-state">Project suggestions will appear here.</div>`;
    return;
  }

  projects.forEach((project) => {
    const stack = Array.isArray(project.techStack) ? project.techStack : [];
    const card = document.createElement("article");
    card.className = "project-card";
    card.innerHTML = `
      <div class="project-top">
        <h4>${escapeHtml(project.name || "Portfolio project")}</h4>
        <span class="tag">${escapeHtml(project.difficulty || "Project")}</span>
      </div>
      <p>${escapeHtml(project.description || "")}</p>
      <p><strong>Phase:</strong> ${escapeHtml(project.phase || "")}</p>
      <div class="tech-list">${stack.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>
    `;
    elements.projectGrid.appendChild(card);
  });
}

function updateStats() {
  const data = state.roadmapData || {};
  elements.timelineStat.textContent = data.estimatedTimeline || "--";
  elements.phaseStat.textContent = String((data.roadmap || []).length);
  elements.gapStat.textContent = String((data.skillGaps || []).length);
}

function updateProgress() {
  const topics = getAllTopicIds();
  const completed = topics.filter((id) => state.progress[id]).length;
  const percent = topics.length ? Math.round((completed / topics.length) * 100) : 0;
  elements.progressValue.textContent = `${percent}%`;
  elements.progressFill.style.width = `${percent}%`;
  elements.progressHint.textContent = topics.length
    ? `${completed} of ${topics.length} roadmap topics completed.`
    : "Generate a roadmap to start tracking each topic.";

  const chartColor = getComputedStyle(document.documentElement).getPropertyValue("--mauve").trim();
  const remainingColor = document.body.classList.contains("dark") ? "rgba(255, 219, 221, 0.16)" : "rgba(91, 49, 19, 0.12)";
  if (state.chart) {
    state.chart.data.datasets[0].data = [percent, 100 - percent];
    state.chart.data.datasets[0].backgroundColor = [chartColor, remainingColor];
    state.chart.update();
  }
}

function initChart() {
  const canvas = document.querySelector("#progressChart");
  state.chart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Completed", "Remaining"],
      datasets: [
        {
          data: [0, 100],
          backgroundColor: ["#A7626B", "rgba(91, 49, 19, 0.12)"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      cutout: "76%",
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
    },
  });
  updateProgress();
}

function getAllTopicIds() {
  return (state.roadmapData?.roadmap || []).flatMap((phase, phaseIndex) =>
    (phase.topics || []).map((topic, topicIndex) => getTopicId(phase, phaseIndex, topic, topicIndex))
  );
}

function getTopicId(phase, phaseIndex, topic, topicIndex) {
  return `${phase.id || phaseIndex}-${topicIndex}-${String(topic).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function loadProgress(roadmapData) {
  const key = progressKey(roadmapData);
  return JSON.parse(localStorage.getItem(key) || "{}");
}

function saveProgress() {
  if (!state.roadmapData) return;
  localStorage.setItem(progressKey(state.roadmapData), JSON.stringify(state.progress));
}

function progressKey(roadmapData) {
  return `${storageScope()}:careerProgress:${roadmapData.targetRole || "role"}`;
}

function persistRoadmap() {
  localStorage.setItem(`${storageScope()}:careerRoadmapData`, JSON.stringify(state.roadmapData));
  localStorage.setItem(`${storageScope()}:careerProfile`, JSON.stringify(state.profile));
}

function restoreSavedRoadmap() {
  const savedData = localStorage.getItem(`${storageScope()}:careerRoadmapData`);
  const savedProfile = localStorage.getItem(`${storageScope()}:careerProfile`);
  if (!savedData) {
    state.roadmapData = null;
    state.profile = {};
    state.progress = {};
    renderAll();
    return;
  }

  state.roadmapData = normalizeRoadmap(JSON.parse(savedData));
  state.profile = savedProfile ? JSON.parse(savedProfile) : {};
  state.progress = loadProgress(state.roadmapData);

  document.querySelector("#name").value = state.profile.name || "";
  document.querySelector("#skills").value = state.profile.skills || "";
  document.querySelector("#experienceLevel").value = state.profile.experienceLevel || "Beginner";
  document.querySelector("#targetRole").value = state.profile.targetRole || "";

  renderAll();
}

function storageScope() {
  return state.user ? `careerUser:${state.user.id}` : "careerGuest";
}

function setLoading(isLoading, label) {
  elements.submitButton.disabled = isLoading;
  elements.submitButton.classList.toggle("loading", isLoading);
  elements.submitText.textContent = label;
}

function appendChat(type, text) {
  const bubble = document.createElement("div");
  bubble.className = `chat-message ${type}`;
  bubble.textContent = text;
  elements.chatWindow.appendChild(bubble);
  elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
  return bubble;
}

function restoreTheme() {
  if (localStorage.getItem("careerTheme") === "dark") {
    document.body.classList.add("dark");
  }
  updateThemeLabel();
}

function updateThemeLabel() {
  elements.themeLabel.textContent = document.body.classList.contains("dark") ? "Dark mode" : "Light mode";
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");
  window.setTimeout(() => elements.toast.classList.remove("show"), 2800);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
