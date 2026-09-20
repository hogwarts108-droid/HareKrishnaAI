const chatUi = {
  de: {back:"Zur Wissensseite", subtitle:"Dein spiritueller AI-Chat", language:"Sprache", title:"Frage die AI", intro:"Antworten zu Bhagavad Gita, Krishna und vedischer Weisheit.", online:"Bereit", welcome:"🙏 Hare Krishna! Was möchtest du wissen?", placeholder:"Deine Frage …", send:"Senden", loading:"Antwort wird vorbereitet …", unavailable:"Der öffentliche Chat ist noch nicht konfiguriert. Bitte hinterlege die Backend-URL in window.BHAKTI_CHAT_API_URL.", error:"Der Chat ist momentan nicht erreichbar. Bitte versuche es später erneut.", note:"Die AI antwortet über das HareKrishnaAI-Backend. Deine lokale Modelladresse bleibt im Browser verborgen.", modeLocal:"Qwen · lokal", modeOnline:"Online-AI", modeSearch:"Suche lokale AI …", localWorking:"Antwortet über dein lokales Qwen-Modell (Ollama).", localMissing:"Lokale AI (Ollama) nicht erreichbar – fallback auf die Online-AI."},
  en: {back:"Back to knowledge", subtitle:"Your spiritual AI chat", language:"Language", title:"Ask the AI", intro:"Answers about the Bhagavad Gita, Krishna and Vedic wisdom.", online:"Ready", welcome:"🙏 Hare Krishna! What would you like to know?", placeholder:"Your question …", send:"Send", loading:"Preparing answer …", unavailable:"The public chat is not configured yet. Set the backend URL in window.BHAKTI_CHAT_API_URL.", error:"The chat is currently unavailable. Please try again later.", note:"The AI responds through the HareKrishnaAI backend. Your local model address stays hidden from the browser.", modeLocal:"Qwen · local", modeOnline:"Online AI", modeSearch:"Searching local AI …", localWorking:"Responds via your local Qwen model (Ollama).", localMissing:"Local AI (Ollama) unreachable – falling back to the online AI."}
};
let chatLanguage = localStorage.getItem("bhaktiai-language") || "de";
const text = key => chatUi[chatLanguage][key];

const LOCAL_AI = {
  base: String(window.BHAKTI_LOCAL_AI_URL || "http://127.0.0.1:11434").replace(/\/$/, ""),
  model: String(window.BHAKTI_LOCAL_AI_MODEL || "qwen-coder-abliterated:latest")
};

let engineMode = "search"; // "search" | "local" | "online"

function renderChatLanguage() {
  document.documentElement.lang = chatLanguage;
  document.querySelectorAll("[data-chat-i18n]").forEach(node => { node.textContent = text(node.dataset.chatI18n); });
  document.querySelectorAll("[data-chat-i18n-placeholder]").forEach(node => { node.placeholder = text(node.dataset.chatI18nPlaceholder); });
}
function addMessage(content, role) {
  const node = document.createElement("div");
  node.className = `chat-message ${role}`;
  node.textContent = content;
  document.querySelector("#chat-messages").append(node);
  node.scrollIntoView({ block: "nearest" });
}
function showTyping() {
  const host = document.querySelector("#chat-messages");
  if (!host) return;
  let el = document.getElementById("typing-indicator");
  if (!el) {
    el = document.createElement("div");
    el.className = "chat-message assistant typing";
    el.id = "typing-indicator";
    const dots = document.createElement("span");
    dots.className = "dots";
    dots.innerHTML = "<i></i><i></i><i></i>";
    el.appendChild(dots);
    host.appendChild(el);
  }
  el.scrollIntoView({ block: "nearest" });
}
function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}
function setEngine(mode) {
  engineMode = mode;
  const badge = document.querySelector("#chat-engine");
  const note = document.querySelector("#chat-note");
  if (badge) {
    if (mode === "local") {
      badge.textContent = text("modeLocal");
      badge.parentElement.classList.add("engine-local");
      badge.parentElement.classList.remove("engine-online");
    } else if (mode === "online") {
      badge.textContent = text("modeOnline");
      badge.parentElement.classList.add("engine-online");
      badge.parentElement.classList.remove("engine-local");
    } else {
      badge.textContent = text("modeSearch");
    }
  }
  if (note) {
    if (mode === "local") {
      note.dataset.i18n = "localWorking";
      note.textContent = text("localWorking");
    } else if (mode === "online") {
      note.dataset.i18n = "localMissing";
      note.textContent = text("localMissing");
    } else {
      note.dataset.i18n = "note";
      note.textContent = text("note");
    }
  }
}
async function detectLocalAI() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const response = await fetch(`${LOCAL_AI.base}/api/version`, { signal: controller.signal });
    clearTimeout(timer);
    if (response.ok) {
      const info = await response.json().catch(() => ({}));
      return Boolean(info.version);
    }
    return false;
  } catch (err) {
    return false;
  }
}
async function askLocalQwen(message) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch(`${LOCAL_AI.base}/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        model: LOCAL_AI.model,
        messages: [
          { role: "system", content: chatLanguage === "de"
            ? "Du bist VedaAmrita, ein freundlicher spiritueller Begleiter. Antworte auf Deutsch, klar und warm, mit Bezug zu Bhagavad Gita, Krishna und vedischer Weisheit. Halte die Antwort nützlich und nicht zu lang."
            : "You are VedaAmrita, a warm spiritual guide. Answer in English, clear and warm, with reference to the Bhagavad Gita, Krishna and Vedic wisdom. Keep the answer useful and not too long." },
          { role: "user", content: message }
        ],
        temperature: 0.7,
        max_tokens: 600
      })
    });
    clearTimeout(timer);
    if (!response.ok) throw new Error(`local http ${response.status}`);
    const data = await response.json().catch(() => null);
    const answer = data?.choices?.[0]?.message?.content;
    if (typeof answer !== "string" || !answer.trim()) throw new Error("empty local answer");
    return answer.trim();
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}
async function answerOnline(message) {
  const apiUrl = (window.BHAKTI_CHAT_API_URL || "").trim();
  if (!apiUrl) {
    const error = document.querySelector("#chat-error");
    error.textContent = text("unavailable");
    error.classList.remove("hidden");
    return false;
  }
  for (let attempt = 1; attempt <= 5; attempt++) {
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, language: chatLanguage })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || text("error"));
      addMessage(data.answer || text("error"), "assistant");
      return true;
    } catch (requestError) {
      if (attempt < 5) {
        await new Promise(resolve => setTimeout(resolve, 8000));
      } else {
        const error = document.querySelector("#chat-error");
        removeTyping();
        error.textContent = requestError.message || text("error");
        error.classList.remove("hidden");
      }
    }
  }
  return false;
}
async function sendMessage(event) {
  event.preventDefault();
  const input = document.querySelector("#chat-input");
  const button = document.querySelector("#chat-send");
  const error = document.querySelector("#chat-error");
  const message = input.value.trim();
  error.classList.add("hidden");
  if (!message) return;
  addMessage(message, "user");
  showTyping();
  input.value = "";
  button.disabled = true;
  button.textContent = text("loading");
  let answered = false;
  if (engineMode === "local") {
    try {
      const localAnswer = await askLocalQwen(message);
      removeTyping();
      addMessage(localAnswer, "assistant");
      answered = true;
    } catch (localError) {
      setEngine("online");
    }
  }
  if (!answered) {
    if (engineMode === "online") {
      answered = await answerOnline(message);
    } else {
      await answerOnline(message);
    }
  }
  removeTyping();
  button.disabled = false;
  button.textContent = text("send");
}
document.querySelector("#chat-language").value = chatLanguage;
document.querySelector("#chat-language").addEventListener("change", event => {
  chatLanguage = event.target.value;
  localStorage.setItem("bhaktiai-language", chatLanguage);
  renderChatLanguage();
  setEngine(engineMode);
});
document.querySelector("#chat-form").addEventListener("submit", sendMessage);
renderChatLanguage();
detectLocalAI().then(ok => { setEngine(ok ? "local" : "online"); });