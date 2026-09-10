(function () {
  const copy = {
    de: {
      badge: "✦ NEU · DEIN SPIRITUELLER COPILOT",
      title: "BhaktiAI <em>im Chat</em>",
      description: "Geschichten, Verse und Antworten – direkt auf Telegram.",
      button: "Chat starten",
      ariaLabel: "BhaktiAI auf Telegram öffnen"
    },
    en: {
      badge: "✦ NEW · YOUR SPIRITUAL COPILOT",
      title: "BhaktiAI <em>in chat</em>",
      description: "Stories, verses and answers – directly on Telegram.",
      button: "Start chat",
      ariaLabel: "Open BhaktiAI on Telegram"
    }
  };

  function updatePromo(language) {
    const languageCopy = copy[language] || copy.de;
    document.querySelectorAll(".chatbot-promo").forEach(promo => {
      promo.querySelector(".promo-badge").textContent = languageCopy.badge;
      promo.querySelector("strong").innerHTML = languageCopy.title;
      promo.querySelector("small").textContent = languageCopy.description;
      promo.querySelector("a span:first-child").textContent = languageCopy.button;
      promo.querySelector("a").setAttribute("aria-label", languageCopy.ariaLabel);
      promo.querySelector("a").href = "https://t.me/HareKrishnaAI_bot";
    });
  }

  const language = localStorage.getItem("bhaktiai-language") || "de";
  updatePromo(language);
  document.querySelectorAll("select").forEach(selector => {
    selector.addEventListener("change", event => {
      const selectedLanguage = event.target.value === "en" ? "en" : "de";
      localStorage.setItem("bhaktiai-language", selectedLanguage);
      updatePromo(selectedLanguage);
    });
  });
})();
