const routePages = [...document.querySelectorAll("[data-route]")];
const routeLinks = [...document.querySelectorAll("[data-route-link]")];
const mobileNavButton = document.querySelector(".mobile-nav-button");
const form = document.querySelector("#chunk-form");
const fileInput = document.querySelector("#video-file");
const dropZone = document.querySelector("#drop-zone");
const selectedFile = document.querySelector("#selected-file");
const fileName = document.querySelector("#file-name");
const fileDetails = document.querySelector("#file-details");
const clearFileButton = document.querySelector("#clear-file");
const processButton = document.querySelector("#process-button");
const resultsPanel = document.querySelector("#results-panel");
const modeOptions = [...document.querySelectorAll(".mode-option")];
let activeRequest = null;

function route() {
  const name = location.hash.replace("#", "") || "home";
  const active = routePages.some((page) => page.dataset.route === name) ? name : "home";
  routePages.forEach((page) => { page.hidden = page.dataset.route !== active; });
  routeLinks.forEach((link) => link.classList.toggle("active", link.dataset.routeLink === active));
  document.body.classList.remove("nav-open");
  mobileNavButton?.setAttribute("aria-expanded", "false");
  window.scrollTo({ top: 0, behavior: "instant" });
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(unit > 1 ? 2 : 0)} ${units[unit]}`;
}

function formatDuration(seconds) {
  const safe = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
    : `${minutes}:${String(secs).padStart(2, "0")}`;
}

function parseTime(value) {
  const trimmed = String(value).trim();
  if (!trimmed) return 0;
  if (/^\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed);
  const parts = trimmed.split(":");
  if (parts.length < 2 || parts.length > 3 || parts.some((part) => !/^\d+(\.\d+)?$/.test(part))) return NaN;
  const values = parts.map(Number);
  if (parts.length === 2) return values[0] * 60 + values[1];
  return values[0] * 3600 + values[1] * 60 + values[2];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showEmptyResults() {
  resultsPanel.innerHTML = `<div class="empty-results"><div class="result-glyph" aria-hidden="true"><span></span><span></span><span></span></div><div><h2>Your parts will appear here</h2><p>Each result will be a separate, playable video file.</p></div></div>`;
}

function chooseFile(file) {
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  fileName.textContent = file.name;
  fileDetails.textContent = `${formatBytes(file.size)} · Ready to process`;
  dropZone.hidden = true;
  selectedFile.hidden = false;
  processButton.disabled = false;
  showEmptyResults();
}

function clearFile() {
  fileInput.value = "";
  selectedFile.hidden = true;
  dropZone.hidden = false;
  processButton.disabled = true;
  showEmptyResults();
}

function showProgress(percent, label, detail, indeterminate = false) {
  resultsPanel.innerHTML = `<div class="processing-state ${indeterminate ? "indeterminate" : ""}">
    <div>
      <div class="result-glyph" aria-hidden="true"><span></span><span></span><span></span></div>
      <h2>${label}</h2>
      <p>${detail}</p>
      <div class="progress-track" aria-label="Processing progress"><div class="progress-bar" style="width:${Math.max(4, percent)}%"></div></div>
    </div>
  </div>`;
}

function showError(message) {
  resultsPanel.innerHTML = `<div class="error-state"><div class="error-icon" aria-hidden="true">!</div><div><h2>Could not create the parts</h2><p>${escapeHtml(message)}</p><button class="secondary-button" type="button" id="retry-button">Review settings and try again</button></div></div>`;
  document.querySelector("#retry-button")?.addEventListener("click", () => document.querySelector("#max-size").focus());
}

function showResults(result) {
  const largest = Math.max(...result.parts.map((part) => part.size));
  resultsPanel.innerHTML = `<div class="result-header"><div><h2>Video parts are ready</h2><p>${escapeHtml(result.source.name)} · ${formatDuration(result.trimmedDuration)} processed</p></div><span class="result-summary">${result.parts.length} ${result.parts.length === 1 ? "part" : "parts"} · largest ${formatBytes(largest)}</span></div>
    <div class="parts-list">
      ${result.parts.map((part, index) => `<div class="part-row">
        <span class="part-index">${String(index + 1).padStart(2, "0")}</span>
        <div class="part-copy"><strong>${escapeHtml(part.name)}</strong><span>${formatDuration(part.duration)} · ${formatBytes(part.size)}</span></div>
        <a class="download-button" href="${part.url}" download>Download</a>
      </div>`).join("")}
    </div>`;
}

async function checkLocalService() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const health = await response.json();
    if (!health.videoTools) throw new Error("Video tools unavailable");
  } catch {
    showError("The local video service is not ready. Restart this site and try again.");
  }
}

window.addEventListener("hashchange", route);
route();
checkLocalService();

mobileNavButton?.addEventListener("click", () => {
  const open = document.body.classList.toggle("nav-open");
  mobileNavButton.setAttribute("aria-expanded", String(open));
});

fileInput.addEventListener("change", () => chooseFile(fileInput.files[0]));
clearFileButton.addEventListener("click", clearFile);

["dragenter", "dragover"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  dropZone.classList.add("dragging");
}));
["dragleave", "drop"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
}));
dropZone.addEventListener("drop", (event) => chooseFile(event.dataTransfer.files[0]));

modeOptions.forEach((option) => option.addEventListener("click", () => {
  modeOptions.forEach((item) => item.classList.toggle("selected", item === option));
}));

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file || activeRequest) return;

  const maxSizeMb = Number(document.querySelector("#max-size").value);
  const trimStart = parseTime(document.querySelector("#trim-start").value);
  const trimEnd = parseTime(document.querySelector("#trim-end").value);
  const mode = document.querySelector('input[name="mode"]:checked').value;

  if (!Number.isFinite(trimStart) || !Number.isFinite(trimEnd) || trimStart < 0 || trimEnd < 0) {
    showError("Use seconds, MM:SS, or HH:MM:SS for both trim fields.");
    return;
  }
  if (!Number.isFinite(maxSizeMb) || maxSizeMb < 1 || maxSizeMb > 2048) {
    showError("Maximum part size must be between 1 and 2048 MB.");
    return;
  }

  const query = new URLSearchParams({
    name: file.name,
    maxSizeMb: String(maxSizeMb),
    trimStart: String(trimStart),
    trimEnd: String(trimEnd),
    mode
  });

  const xhr = new XMLHttpRequest();
  activeRequest = xhr;
  processButton.disabled = true;
  processButton.querySelector("span:first-child").textContent = "Working…";
  showProgress(4, "Uploading video", "Preparing the local working copy…");

  xhr.open("POST", `/api/chunk?${query}`);
  xhr.setRequestHeader("Content-Type", "application/octet-stream");
  xhr.upload.addEventListener("progress", (progressEvent) => {
    if (!progressEvent.lengthComputable) return;
    const percent = Math.min(100, Math.round((progressEvent.loaded / progressEvent.total) * 100));
    if (percent < 100) showProgress(percent, `Uploading video · ${percent}%`, `${formatBytes(progressEvent.loaded)} of ${formatBytes(progressEvent.total)}`);
    else showProgress(100, "Creating video parts", "This can take a little while for large videos.", true);
  });
  xhr.addEventListener("load", () => {
    try {
      const result = JSON.parse(xhr.responseText || "{}");
      if (xhr.status < 200 || xhr.status >= 300) throw new Error(result.error || "Video processing failed.");
      showResults(result);
    } catch (error) {
      showError(error.message || "Video processing failed.");
    } finally {
      activeRequest = null;
      processButton.disabled = false;
      processButton.querySelector("span:first-child").textContent = "Create video parts";
    }
  });
  xhr.addEventListener("error", () => {
    activeRequest = null;
    processButton.disabled = false;
    processButton.querySelector("span:first-child").textContent = "Create video parts";
    showError("The local connection was interrupted. Keep this page open and try again.");
  });
  xhr.send(file);
});

