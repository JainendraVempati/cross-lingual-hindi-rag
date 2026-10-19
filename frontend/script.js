
const form = document.getElementById("question-form");
const questionInput = document.getElementById("question");
const submitButton = document.getElementById("submit-button");
const buttonText = document.getElementById("button-text");
const charCount = document.getElementById("char-count");
const results = document.getElementById("results");
const errorBox = document.getElementById("error-box");
const answerText = document.getElementById("answer-text");
const sourcesList = document.getElementById("sources-list");
const sourceCount = document.getElementById("source-count");
const elapsedTime = document.getElementById("elapsed-time");

questionInput.addEventListener("input", () => {
  charCount.textContent = `${questionInput.value.length} / 2000`;
});

document.querySelectorAll(".example-chip").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    charCount.textContent = `${questionInput.value.length} / 2000`;
    questionInput.focus();
  });
});

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function makePill(text, extraClass = "") {
  const pill = document.createElement("span");
  pill.className = `meta-pill ${extraClass}`.trim();
  pill.textContent = text;
  return pill;
}

function renderSources(sources) {
  sourcesList.replaceChildren();
  sourceCount.textContent = `${sources.length} retrieved`;

  sources.forEach((source, index) => {
    const card = document.createElement("article");
    card.className = "source-card";

    const top = document.createElement("div");
    top.className = "source-top";

    const title = document.createElement("div");
    title.className = "source-title";
    title.textContent = `Source ${index + 1} · ${source.section || "Untitled section"}`;

    const score = makePill(
      `Similarity: ${Number(source.score).toFixed(3)}`,
      "score-pill"
    );

    top.append(title, score);

    const metadata = document.createElement("div");
    metadata.className = "source-meta";

    metadata.append(
      makePill(`Page ${source.page}`),
      makePill(`Chunk: ${source.chunk_id}`)
    );

    const content = document.createElement("p");
    content.className = "source-content";
    content.textContent = source.content || "";

    card.append(top, metadata, content);
    sourcesList.append(card);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();

  if (!question) {
    showError("Please enter a question first.");
    questionInput.focus();
    return;
  }

  errorBox.hidden = true;
  results.hidden = true;
  submitButton.disabled = true;
  buttonText.textContent = "Searching...";
  answerText.textContent = "";
  sourcesList.replaceChildren();

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });

    const rawResponse = await response.text();

let data;

try {
  data = JSON.parse(rawResponse);
} catch {
  throw new Error(
    `Backend returned invalid JSON (HTTP ${response.status}). ` +
    `Response: ${rawResponse || "(empty response)"}`
  );
}

    if (!response.ok) {
      throw new Error(data.detail || "The request failed.");
    }

    answerText.textContent = data.answer || "No answer was returned.";
    renderSources(data.sources || []);

    elapsedTime.textContent =
      `${Number(data.elapsed_seconds || 0).toFixed(2)} seconds`;

    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(
      error.message ||
      "Could not connect to the backend. Check whether the API server is running."
    );
  } finally {
    submitButton.disabled = false;
    buttonText.textContent = "Ask question";
  }
});
