/**
 * T&C Guardian — Popup Controller
 *
 * This script handles the full lifecycle of a scan:
 *   1. User clicks "Scan This Page"
 *   2. We grab the active tab's URL via chrome.tabs API
 *   3. We POST the URL to http://localhost:8000/scan
 *   4. We render the score card and findings list
 *
 * Error handling:
 *   - Network failures (backend not running)
 *   - HTTP 4xx from the backend (scrape/analysis errors)
 *   - Unexpected response shapes
 */

document.getElementById("scanBtn").addEventListener("click", async () => {
  const scanBtn = document.getElementById("scanBtn");
  const loading = document.getElementById("loading");
  const scoreCard = document.getElementById("scoreCard");
  const findingsTitle = document.getElementById("findingsTitle");
  const findingsList = document.getElementById("findingsList");
  const errorMsg = document.getElementById("errorMsg");


  scanBtn.disabled = true;
  scanBtn.textContent = "Scanning…";
  loading.style.display = "block";
  scoreCard.style.display = "none";
  findingsTitle.style.display = "none";
  findingsList.innerHTML = "";
  errorMsg.style.display = "none";

  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    if (!tab || !tab.url || !tab.url.startsWith("http")) {
      throw new Error(
        "Cannot scan this page. Navigate to a website first."
      );
    }

    const response = await fetch("http://localhost:8000/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: tab.url }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Server returned ${response.status}`
      );
    }

    const data = await response.json();

    loading.style.display = "none";
    scoreCard.style.display = "block";

    const gradeEl = document.getElementById("gradeDisplay");
    gradeEl.textContent = data.grade;

    if (["A", "B"].includes(data.grade)) {
      gradeEl.style.color = "#16a34a"; // green
    } else if (data.grade === "C") {
      gradeEl.style.color = "#ca8a04"; // amber
    } else {
      gradeEl.style.color = "#dc2626"; // red
    }

    document.getElementById("scoreDisplay").textContent =
      `Safety Score: ${data.score}/100`;
    document.getElementById("summaryDisplay").textContent =
      data.summary;

    if (data.findings && data.findings.length > 0) {
      findingsTitle.style.display = "block";

      const severityOrder = {
        Critical: 0,
        High: 1,
        Medium: 2,
        Low: 3,
      };

      const sorted = [...data.findings].sort(
        (a, b) =>
          (severityOrder[a.severity] ?? 4) -
          (severityOrder[b.severity] ?? 4)
      );

      sorted.forEach((finding) => {
        const card = document.createElement("div");
        const sevClass = finding.severity.toLowerCase();

        card.className = `finding-card border-${sevClass}`;
        card.innerHTML = `
          <div class="badge-row">
            <span class="severity-badge ${sevClass}">${finding.severity}</span>
            <span class="category-label">${finding.category}</span>
          </div>
          <div class="finding-text">${escapeHtml(finding.finding)}</div>
        `;

        findingsList.appendChild(card);
      });
    }
  } catch (err) {
    loading.style.display = "none";
    errorMsg.style.display = "block";
    errorMsg.textContent = err.message || "An unexpected error occurred.";
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan This Page";
  }
});


function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}