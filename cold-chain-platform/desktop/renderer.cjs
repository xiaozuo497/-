const statusText = document.querySelector("[data-status-text]");
const statusDot = document.querySelector("[data-status-dot]");
const logBox = document.querySelector("[data-log]");
const startButton = document.querySelector("[data-start]");
const stopButton = document.querySelector("[data-stop]");
const browserButton = document.querySelector("[data-browser]");
const rootText = document.querySelector("[data-root]");

function setStatus(payload) {
  statusText.textContent = payload.message || "准备启动";
  statusDot.dataset.state = payload.state || "idle";
}

window.desktopApi.onStatus(setStatus);
window.desktopApi.onLog((line) => {
  const div = document.createElement("div");
  div.textContent = line;
  logBox.appendChild(div);
  logBox.scrollTop = logBox.scrollHeight;
});

startButton.addEventListener("click", () => window.desktopApi.start());
stopButton.addEventListener("click", () => window.desktopApi.stop());
browserButton.addEventListener("click", () => window.desktopApi.openExternal());

window.desktopApi.projectRoot().then((root) => {
  rootText.textContent = root;
});
