(function () {
  const page = location.pathname.split("/").pop();
  const translations = {
    books: {
      de: { title: "Bücher", intro: "Originale Bücher mit unveränderten Seiten und Illustrationen.", home: "← Zur Startseite", read: "Buch öffnen", folder: "Mappe öffnen", german: ["Die vollständige deutsche Originalausgabe.", "Deutsche Cantos 1 bis 10.", "Fünf deutsche Krishna-Bände.", "Deutsche Adi-, Madhya- und Antya-lila-Bände.", "Deutsche Originalausgabe mit unveränderten Originalseiten.", "Deutsche Ausgabe von 1969 mit den Originalseiten."], headings: ["Bhagavad-gita", "Srimad-Bhagavatam", "Krishna-Bücher", "Caitanya-caritamrta", "Der Nektar der Unterweisung", "Sri Isopanisad"] },
      en: { title: "Books", intro: "Original books with unchanged pages and illustrations.", home: "← Home", read: "Open book", folder: "Open collection", german: ["The complete German original edition.", "German Cantos 1 to 10.", "Five German Krishna volumes.", "German Adi-, Madhya- and Antya-lila volumes.", "German original edition with unchanged pages.", "German edition from 1969 with the original pages."], headings: ["Bhagavad-gita", "Srimad-Bhagavatam", "Krishna Books", "Caitanya-caritamrta", "The Nectar of Instruction", "Sri Isopanisad"] }
    },
    bhagavatam: {
      de: { subtitle: "Deutsche Cantos als einzelne Original-PDF-Bände.", back: "← Zur Bücherseite", read: "Buch lesen" },
      en: { subtitle: "German cantos as individual original PDF volumes.", back: "← Back to books", read: "Read book" }
    },
    krishna: {
      de: { title: "Krishna-Bücher", subtitle: "Die deutschen Krishna-Bände als einzelne Original-PDF-Bücher.", back: "← Zur Bücherseite", read: "Buch lesen" },
      en: { title: "Krishna Books", subtitle: "German Krishna volumes as individual original PDF books.", back: "← Back to books", read: "Read book" }
    },
    caitanya: {
      de: { title: "Caitanya-caritamrta", subtitle: "Deutsche Original-PDF-Bände, nach Lila und Teil geordnet.", back: "← Zur Bücherseite", read: "Buch lesen", sections: ["Adi-lila", "Madhya-lila", "Antya-lila"] },
      en: { title: "Caitanya-caritamrta", subtitle: "German original PDF volumes, arranged by lila and part.", back: "← Back to books", read: "Read book", sections: ["Adi-lila", "Madhya-lila", "Antya-lila"] }
    }
  };

  const key = page === "books.html" ? "books" : page === "bhagavatam.html" ? "bhagavatam" : page === "krishna-books.html" ? "krishna" : page === "caitanya.html" ? "caitanya" : null;
  if (!key) return;
  const selector = document.querySelector(".site-language-bar select");
  const setLanguage = value => {
    const language = value === "en" ? "en" : "de";
    const text = translations[key][language];
    document.documentElement.lang = language;
    localStorage.setItem("bhaktiai-language", language);
    if (key === "books") {
      document.querySelector("header h1").textContent = text.title;
      document.querySelector("header p").textContent = text.intro;
      document.querySelector(".nav a").textContent = text.home;
      const german = document.querySelectorAll("#german-collections > section");
      german.forEach((section, index) => {
        section.querySelector("h2").textContent = `${text.headings[index]}`;
        section.querySelector("p").textContent = text.german[index];
        section.querySelector(".button").textContent = index < 4 ? text.folder : text.read;
      });
    } else {
      const title = document.querySelector("#page-title") || document.querySelector("header h1");
      const subtitle = document.querySelector("#page-subtitle") || document.querySelector("header p");
      const back = document.querySelector("#back-link") || document.querySelector(".nav a");
      if (title && text.title) title.textContent = text.title;
      if (subtitle) subtitle.textContent = text.subtitle;
      if (back) back.textContent = text.back;
      document.querySelectorAll(".books-grid .button").forEach(button => { button.textContent = text.read; });
      if (text.sections) document.querySelectorAll("main > section > h2").forEach((heading, index) => { heading.textContent = text.sections[index]; });
    }
  };
  selector.value = localStorage.getItem("bhaktiai-language") || "de";
  selector.addEventListener("change", event => setLanguage(event.target.value));
  setLanguage(selector.value);
})();
