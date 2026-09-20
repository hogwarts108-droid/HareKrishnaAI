const chatUi = {
  de: {back:"Zur Wissensseite", subtitle:"Dein spiritueller AI-Chat", language:"Sprache", title:"Frage die AI", intro:"Antworten zu Bhagavad Gita, Krishna und vedischer Weisheit.", online:"Bereit", welcome:"🙏 Hare Krishna! Was möchtest du wissen?", placeholder:"Deine Frage …", send:"Senden", loading:"Antwort wird vorbereitet …", unavailable:"Der öffentliche Chat ist noch nicht konfiguriert. Bitte hinterlege die Backend-URL in window.BHAKTI_CHAT_API_URL.", error:"Der Chat ist momentan nicht erreichbar. Bitte versuche es später erneut.", note:"Die AI antwortet über das HareKrishnaAI-Backend. Deine lokale Modelladresse bleibt im Browser verborgen."},
  en: {back:"Back to knowledge", subtitle:"Your spiritual AI chat", language:"Language", title:"Ask the AI", intro:"Answers about the Bhagavad Gita, Krishna and Vedic wisdom.", online:"Ready", welcome:"🙏 Hare Krishna! What would you like to know?", placeholder:"Your question …", send:"Send", loading:"Preparing answer …", unavailable:"The public chat is not configured yet. Set the backend URL in window.BHAKTI_CHAT_API_URL.", error:"The chat is currently unavailable. Please try again later.", note:"The AI responds through the HareKrishnaAI backend. Your local model address stays hidden from the browser."}
};
let chatLanguage = localStorage.getItem("bhaktiai-language") || "de";
const text = key => chatUi[chatLanguage][key];
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
async function sendMessage(event) {
  event.preventDefault();
  const input = document.querySelector("#chat-input");
  const button = document.querySelector("#chat-send");
  const error = document.querySelector("#chat-error");
  const message = input.value.trim();
  const apiUrl = (window.BHAKTI_CHAT_API_URL || "").trim();
  error.classList.add("hidden");
  if (!message) return;
  if (!apiUrl) {
    error.textContent = text("unavailable");
    error.classList.remove("hidden");
    return;
  }
  addMessage(message, "user");
  showTyping();
  input.value = "";
  button.disabled = true;
  button.textContent = text("loading");
  for (let attempt = 1; attempt <= 5; attempt++) {
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, language: chatLanguage })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || text("error"));
      removeTyping();
      addMessage(data.answer || text("error"), "assistant");
      break;
    } catch (requestError) {
      if (attempt < 5) {
        await new Promise(resolve => setTimeout(resolve, 8000));
      } else {
        removeTyping();
        error.textContent = requestError.message || text("error");
        error.classList.remove("hidden");
      }
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
});
document.querySelector("#chat-form").addEventListener("submit", sendMessage);
renderChatLanguage();
