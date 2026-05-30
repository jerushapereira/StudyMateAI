const notesInput = document.getElementById("notesInput");
const notesFile = document.getElementById("notesFile");
const fileName = document.getElementById("fileName");
const questionInput = document.getElementById("questionInput");

const summarizeBtn = document.getElementById("summarizeBtn");
const quizBtn = document.getElementById("quizBtn");
const flashcardsBtn = document.getElementById("flashcardsBtn");
const studyPlanBtn = document.getElementById("studyPlanBtn");
const askBtn = document.getElementById("askBtn");
const saveSummaryBtn = document.getElementById("saveSummaryBtn");
const loadSavedBtn = document.getElementById("loadSavedBtn");
const downloadSummaryBtn = document.getElementById("downloadSummaryBtn");
const copyOutputBtn = document.getElementById("copyOutputBtn");
const sampleNotesBtn = document.getElementById("sampleNotesBtn");
const clearNotesBtn = document.getElementById("clearNotesBtn");

const loadingCard = document.getElementById("loadingCard");
const loadingText = document.getElementById("loadingText");
const errorCard = document.getElementById("errorCard");

const summaryContent = document.querySelector("#summaryResult .result-content");
const quizContent = document.querySelector("#quizResult .result-content");
const flashcardsContent = document.querySelector("#flashcardsResult .result-content");
const planContent = document.querySelector("#planResult .result-content");
const answerContent = document.querySelector("#answerResult .result-content");

const progressFill = document.getElementById("progressFill");
const progressLabel = document.getElementById("progressLabel");
const summaryCount = document.getElementById("summaryCount");
const quizCount = document.getElementById("quizCount");
const askCount = document.getElementById("askCount");
const savedSummaryStatus = document.getElementById("savedSummaryStatus");
const wordCount = document.getElementById("wordCount");
const readTime = document.getElementById("readTime");
const autoSaveStatus = document.getElementById("autoSaveStatus");

const themeToggle = document.getElementById("themeToggle");
const timerDisplay = document.getElementById("timerDisplay");
const startTimerBtn = document.getElementById("startTimerBtn");
const resetTimerBtn = document.getElementById("resetTimerBtn");

const STORAGE_KEYS = {
    theme: "studymate_theme",
    summary: "studymate_saved_summary",
    notes: "studymate_draft_notes",
    stats: "studymate_stats",
};

let latestSummary = "";
let latestOutput = "";
let timerSeconds = 25 * 60;
let timerId = null;
let stats = loadStats();

const sampleNotes = `Photosynthesis is the process by which green plants make food using sunlight.
The main raw materials are carbon dioxide from air and water from soil.
Chlorophyll in leaves absorbs sunlight.
The products are glucose and oxygen.
Photosynthesis mainly happens in chloroplasts.
The word equation is: carbon dioxide + water -> glucose + oxygen.
It is important because it provides food for plants and oxygen for living organisms.`;

notesInput.value = localStorage.getItem(STORAGE_KEYS.notes) || "";
updateStatsUI();
updateSavedSummaryStatus();
loadTheme();
updateTimerDisplay();
updateNotesMeta();

notesInput.addEventListener("input", () => {
    localStorage.setItem(STORAGE_KEYS.notes, notesInput.value);
    autoSaveStatus.textContent = "Draft saved";
    updateNotesMeta();
});

notesFile.addEventListener("change", () => {
    const selectedFile = notesFile.files[0];
    fileName.textContent = selectedFile ? selectedFile.name : "No file selected";
});

summarizeBtn.addEventListener("click", generateSummary);
quizBtn.addEventListener("click", generateQuiz);
flashcardsBtn.addEventListener("click", generateFlashcards);
studyPlanBtn.addEventListener("click", generateStudyPlan);
askBtn.addEventListener("click", askAI);
saveSummaryBtn.addEventListener("click", saveSummary);
loadSavedBtn.addEventListener("click", loadSavedSummary);
downloadSummaryBtn.addEventListener("click", downloadSummary);
copyOutputBtn.addEventListener("click", copyLatestOutput);
sampleNotesBtn.addEventListener("click", () => {
    notesInput.value = sampleNotes;
    localStorage.setItem(STORAGE_KEYS.notes, sampleNotes);
    updateNotesMeta();
    hideError();
});
clearNotesBtn.addEventListener("click", () => {
    notesInput.value = "";
    notesFile.value = "";
    fileName.textContent = "No file selected";
    localStorage.removeItem(STORAGE_KEYS.notes);
    updateNotesMeta();
});

themeToggle.addEventListener("click", toggleTheme);
startTimerBtn.addEventListener("click", toggleTimer);
resetTimerBtn.addEventListener("click", resetTimer);

async function generateSummary() {
    const formData = createNotesFormData();
    if (!hasNotes(formData)) return;

    try {
        setLoading(true, "Creating a clean summary...");
        const data = await postFormData("/api/summarize", formData);
        latestSummary = data.summary;
        showResult(summaryContent, data.summary);
        updateStats("summary");
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

async function generateQuiz() {
    const formData = createNotesFormData();
    if (!hasNotes(formData)) return;

    try {
        setLoading(true, "Building quiz questions...");
        const data = await postFormData("/api/quiz", formData);
        showResult(quizContent, data.quiz);
        updateStats("quiz");
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

async function generateFlashcards() {
    const formData = createNotesFormData();
    if (!hasNotes(formData)) return;

    try {
        setLoading(true, "Turning notes into flashcards...");
        const data = await postFormData("/api/flashcards", formData);
        showResult(flashcardsContent, data.flashcards);
        updateStats("quiz");
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

async function generateStudyPlan() {
    const formData = createNotesFormData();
    if (!hasNotes(formData)) return;

    try {
        setLoading(true, "Planning your revision session...");
        const data = await postFormData("/api/study-plan", formData);
        showResult(planContent, data.study_plan);
        updateStats("summary");
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

async function askAI() {
    const question = questionInput.value.trim();

    if (!notesInput.value.trim() && (!notesFile.files[0] || notesFile.files[0].size === 0)) {
        showError("Please paste notes or upload a .txt/.md file before asking a question.");
        return;
    }

    if (!question) {
        showError("Please type a question first.");
        return;
    }

    try {
        setLoading(true, "Thinking through your doubt...");
        const formData = createNotesFormData();
        formData.append("question", question);
        const data = await postFormData("/api/ask", formData);
        showResult(answerContent, data.answer);
        updateStats("ask");
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

function createNotesFormData() {
    const formData = new FormData();
    formData.append("notes", notesInput.value.trim());

    if (notesFile.files[0]) {
        formData.append("notes_file", notesFile.files[0]);
    }

    return formData;
}

function hasNotes(formData) {
    const pastedNotes = formData.get("notes");
    const uploadedFile = formData.get("notes_file");

    if (!pastedNotes && (!uploadedFile || uploadedFile.size === 0)) {
        showError("Please paste notes or upload a .txt/.md file first.");
        return false;
    }

    hideError();
    return true;
}

async function postFormData(url, formData) {
    const response = await fetch(url, {
        method: "POST",
        body: formData,
    });

    return handleResponse(response);
}

async function handleResponse(response) {
    const data = await response.json();

    if (!response.ok || data.success === false) {
        throw new Error(data.error || "Something went wrong. Please try again.");
    }

    return data;
}

function showResult(element, text) {
    latestOutput = text;
    element.textContent = text;
    element.classList.remove("empty");
    document.getElementById("output").scrollIntoView({ behavior: "smooth", block: "start" });
}

function setLoading(isLoading, message = "Generating response...") {
    loadingText.textContent = message;
    loadingCard.classList.toggle("hidden", !isLoading);

    [summarizeBtn, quizBtn, flashcardsBtn, studyPlanBtn, askBtn].forEach((button) => {
        button.disabled = isLoading;
    });
}

function showError(message) {
    errorCard.textContent = message;
    errorCard.classList.remove("hidden");
}

function hideError() {
    errorCard.classList.add("hidden");
}

function saveSummary() {
    if (!latestSummary) {
        showError("Generate a summary before saving.");
        return;
    }

    localStorage.setItem(STORAGE_KEYS.summary, latestSummary);
    updateSavedSummaryStatus();
    hideError();
}

function loadSavedSummary() {
    const savedSummary = localStorage.getItem(STORAGE_KEYS.summary);

    if (!savedSummary) {
        showError("No saved summary found in this browser.");
        return;
    }

    latestSummary = savedSummary;
    showResult(summaryContent, savedSummary);
    hideError();
}

function updateSavedSummaryStatus() {
    const savedSummary = localStorage.getItem(STORAGE_KEYS.summary);
    savedSummaryStatus.textContent = savedSummary
        ? "One summary is saved in this browser."
        : "No saved summary yet.";
}

function downloadSummary() {
    if (!latestSummary) {
        showError("Generate or load a summary before downloading.");
        return;
    }

    const blob = new Blob([latestSummary], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "studymate-summary.txt";
    link.click();
    URL.revokeObjectURL(link.href);
}

async function copyLatestOutput() {
    if (!latestOutput) {
        showError("Generate an AI response before copying.");
        return;
    }

    await navigator.clipboard.writeText(latestOutput);
    copyOutputBtn.textContent = "Copied";
    setTimeout(() => {
        copyOutputBtn.textContent = "Copy latest";
    }, 1200);
}

function updateNotesMeta() {
    const words = notesInput.value.trim().split(/\s+/).filter(Boolean).length;
    const minutes = Math.ceil(words / 180);
    wordCount.textContent = `${words} words`;
    readTime.textContent = `${minutes} min read`;
}

function loadStats() {
    const savedStats = localStorage.getItem(STORAGE_KEYS.stats);
    return savedStats
        ? JSON.parse(savedStats)
        : { summary: 0, quiz: 0, ask: 0 };
}

function updateStats(type) {
    stats[type] += 1;
    localStorage.setItem(STORAGE_KEYS.stats, JSON.stringify(stats));
    updateStatsUI();
}

function updateStatsUI() {
    const total = stats.summary + stats.quiz + stats.ask;
    const progress = Math.min(total * 20, 100);

    summaryCount.textContent = stats.summary;
    quizCount.textContent = stats.quiz;
    askCount.textContent = stats.ask;
    progressFill.style.width = `${progress}%`;
    progressLabel.textContent = `${progress}%`;
}

function loadTheme() {
    const savedTheme = localStorage.getItem(STORAGE_KEYS.theme);
    if (savedTheme === "dark") {
        document.body.classList.add("dark");
    }
}

function toggleTheme() {
    document.body.classList.toggle("dark");
    const isDark = document.body.classList.contains("dark");
    localStorage.setItem(STORAGE_KEYS.theme, isDark ? "dark" : "light");
}

function toggleTimer() {
    if (timerId) {
        clearInterval(timerId);
        timerId = null;
        startTimerBtn.textContent = "Start";
        return;
    }

    startTimerBtn.textContent = "Pause";
    timerId = setInterval(() => {
        timerSeconds -= 1;
        updateTimerDisplay();

        if (timerSeconds <= 0) {
            clearInterval(timerId);
            timerId = null;
            startTimerBtn.textContent = "Start";
            timerSeconds = 25 * 60;
            updateTimerDisplay();
            showError("Pomodoro complete. Take a short break!");
        }
    }, 1000);
}

function resetTimer() {
    clearInterval(timerId);
    timerId = null;
    timerSeconds = 25 * 60;
    startTimerBtn.textContent = "Start";
    updateTimerDisplay();
}

function updateTimerDisplay() {
    const minutes = Math.floor(timerSeconds / 60).toString().padStart(2, "0");
    const seconds = (timerSeconds % 60).toString().padStart(2, "0");
    timerDisplay.textContent = `${minutes}:${seconds}`;
}
