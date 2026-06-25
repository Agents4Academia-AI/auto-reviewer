// Poll the job status until it finishes, then render the markdown report.
(function () {
  const panel = document.getElementById("status-panel");
  if (!panel) return;
  const jobId = panel.dataset.jobId;
  const total = parseInt(panel.dataset.total, 10) || 11;

  const badge = document.getElementById("status-badge");
  const statusText = document.getElementById("status-text");
  const bar = document.getElementById("progress-bar");
  const errorText = document.getElementById("error-text");
  const report = document.getElementById("report");
  const cancelBtn = document.getElementById("cancel-btn");

  const POLL_MS = 3000;
  let cancelling = false; // true once the user has clicked Cancel

  // Human-readable names for each pipeline stage (see pipeline.py / prompts.py).
  const STAGE_LABELS = {
    stage_0: "Parsing Paper",
    stage_1: "Building Overall Understanding",
    stage_2: "Analyzing Sections",
    stage_3: "Extracting Claims",
    stage_4: "Checking Novelty",
    stage_5: "Assessing Significance",
    stage_6: "Checking Rigor",
    stage_7: "Planning the Review",
    stage_8: "Drafting the Review",
    stage_9: "Self-Critiquing",
    stage_10: "Finalizing Review",
  };

  // "stage_0" -> "Parsing Paper… (Stage 0)"
  function stageLabel(stage) {
    if (!stage) return "";
    const name = STAGE_LABELS[stage] || stage;
    const m = /stage_(\d+)/.exec(stage);
    const num = m ? ` (Stage ${m[1]})` : "";
    return `${name}…${num}`;
  }

  function setBadge(status) {
    badge.textContent = status;
    badge.className = "badge badge-" + status;
  }

  // Custom confirm dialog so the buttons read "No" / "Yes" rather than the
  // browser's fixed "Cancel" / "OK". Resolves true only when "Yes" is chosen.
  function confirmDialog(message) {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      overlay.innerHTML =
        '<div class="modal" role="dialog" aria-modal="true">' +
        "<p></p>" +
        '<div class="modal-actions">' +
        '<button type="button" class="modal-btn modal-btn-no">No</button>' +
        '<button type="button" class="modal-btn modal-btn-yes">Yes</button>' +
        "</div></div>";
      overlay.querySelector("p").textContent = message;

      function close(result) {
        document.removeEventListener("keydown", onKey);
        overlay.remove();
        resolve(result);
      }
      function onKey(e) {
        if (e.key === "Escape") close(false);
      }

      overlay.querySelector(".modal-btn-no").addEventListener("click", () => close(false));
      overlay.querySelector(".modal-btn-yes").addEventListener("click", () => close(true));
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) close(false); // click outside the card = No
      });
      document.addEventListener("keydown", onKey);

      document.body.appendChild(overlay);
      overlay.querySelector(".modal-btn-yes").focus();
    });
  }

  async function loadReport() {
    const res = await fetch(`/api/review/${jobId}/markdown`);
    if (!res.ok) return;
    const md = await res.text();
    report.innerHTML = window.marked ? marked.parse(md) : md;
    report.hidden = false;
  }

  // The cancel button is only rendered for the review's owner.
  if (cancelBtn) {
    cancelBtn.addEventListener("click", async () => {
      if (!(await confirmDialog("Cancel this review?"))) return;
      cancelBtn.disabled = true;
      cancelling = true;
      statusText.textContent = "Cancelling…";
      try {
        await fetch(`/api/review/${jobId}/cancel`, { method: "POST" });
      } catch (e) {
        // The next poll will reflect the real state regardless.
      }
    });
  }

  async function tick() {
    let data;
    try {
      const res = await fetch(`/api/review/${jobId}`);
      if (!res.ok) throw new Error("status " + res.status);
      data = await res.json();
    } catch (e) {
      statusText.textContent = "Connection issue, retrying…";
      setTimeout(tick, POLL_MS);
      return;
    }

    setBadge(data.status);
    const active = data.status === "queued" || data.status === "running";
    if (cancelBtn) cancelBtn.hidden = !active;

    if (data.status === "queued") {
      if (!cancelling) statusText.textContent = "Waiting in queue…";
      bar.style.width = "0%";
      setTimeout(tick, POLL_MS);
    } else if (data.status === "running") {
      const idx = data.stage_index || 0;
      if (!cancelling) {
        statusText.textContent = data.current_stage
          ? `${stageLabel(data.current_stage)}`
          : `Stage ${idx} of ${total}`;
      }
      bar.style.width = Math.round((idx / total) * 100) + "%";
      setTimeout(tick, POLL_MS);
    } else if (data.status === "done") {
      statusText.textContent = "Complete";
      bar.style.width = "100%";
      loadReport();
    } else if (data.status === "cancelled") {
      statusText.textContent = "Cancelled";
      bar.style.width = "0%";
    } else if (data.status === "failed") {
      statusText.textContent = "Failed";
      errorText.textContent = data.error || "Unknown error.";
      errorText.hidden = false;
    }
  }

  tick();
})();
