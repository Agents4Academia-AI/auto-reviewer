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

  function setBadge(status) {
    badge.textContent = status;
    badge.className = "badge badge-" + status;
  }

  async function loadReport() {
    const res = await fetch(`/api/review/${jobId}/markdown`);
    if (!res.ok) return;
    const md = await res.text();
    report.innerHTML = window.marked ? marked.parse(md) : md;
    report.hidden = false;
  }

  cancelBtn.addEventListener("click", async () => {
    if (!confirm("Cancel this review?")) return;
    cancelBtn.disabled = true;
    cancelling = true;
    statusText.textContent = "Cancelling…";
    try {
      await fetch(`/api/review/${jobId}/cancel`, { method: "POST" });
    } catch (e) {
      // The next poll will reflect the real state regardless.
    }
  });

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
    cancelBtn.hidden = !active;

    if (data.status === "queued") {
      if (!cancelling) statusText.textContent = "Waiting in queue…";
      bar.style.width = "0%";
      setTimeout(tick, POLL_MS);
    } else if (data.status === "running") {
      const idx = data.stage_index || 0;
      if (!cancelling) {
        statusText.textContent = `Running — stage ${idx} of ${total}` +
          (data.current_stage ? ` (${data.current_stage})` : "");
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
