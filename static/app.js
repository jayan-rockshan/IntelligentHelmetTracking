// static/app.js
const tbody = document.querySelector("#plateTable tbody");
const rowCount = document.getElementById("rowCount");
const searchInput = document.getElementById("search");
const refreshBtn = document.getElementById("btnRefresh");
const downloadBtn = document.getElementById("btnDownload");

async function loadTable({ limit = 100, q = "" } = {}) {
  const params = new URLSearchParams({ limit });
  if (q) params.set("q", q);

  const res = await fetch(`/api/plates?${params.toString()}`);
  const data = await res.json();

  tbody.innerHTML = "";
  for (const r of data) {
    const tr = document.createElement("tr");

    const tdId = document.createElement("td");
    tdId.textContent = r.id;

    const tdFrame = document.createElement("td");
    tdFrame.textContent = r.frame_number;

    const tdText = document.createElement("td");
    tdText.textContent = r.plate_text || "";

    const tdSnap = document.createElement("td");
    if (r.plate_image_path) {
      const a = document.createElement("a");
      const filename = r.plate_image_path.split(/[\\/]/).pop();
      a.href = `/snaps/${filename}`;
      a.target = "_blank";
      a.textContent = "view";
      tdSnap.appendChild(a);
    } else {
      tdSnap.textContent = "-";
    }

    const tdAt = document.createElement("td");
    tdAt.textContent = r.detected_at ? new Date(r.detected_at).toLocaleString() : "";

    tr.append(tdId, tdFrame, tdText, tdSnap, tdAt);
    tbody.appendChild(tr);
  }
  rowCount.textContent = `${data.length} rows`;

  // Update download link with same filters
  const dl = new URLSearchParams({ limit });
  if (q) dl.set("q", q);
  downloadBtn.href = `/download?${dl.toString()}`;
}

refreshBtn.addEventListener("click", () => {
  loadTable({ limit: 100, q: searchInput.value.trim() });
});

searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    loadTable({ limit: 100, q: searchInput.value.trim() });
  }
});

// Auto-refresh table every 5 seconds
setInterval(() => {
  loadTable({ limit: 100, q: searchInput.value.trim() });
}, 5000);

// Initial load
loadTable();


// charts////////////////////////////////////////

let barChart, pieChart;

async function loadCharts() {
  const res = await fetch("/api/stats");
  const stats = await res.json();

  // --- Bar chart ---
  const labels = stats.bar.map(r => r.d);
  const values = stats.bar.map(r => r.c);

  if (barChart) barChart.destroy();
  barChart = new Chart(document.getElementById("barChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Violations per Day",
        data: values,
        backgroundColor: "#3da9fc"
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } }
    }
  });

  // --- Pie chart (Top 5 plates) ---
  const pieLabels = stats.pie.map(r => r.label || "Unknown");
  const pieValues = stats.pie.map(r => r.c);

  if (pieChart) pieChart.destroy();
  pieChart = new Chart(document.getElementById("pieChart"), {
    type: "pie",
    data: {
      labels: pieLabels,
      datasets: [{
        data: pieValues,
        backgroundColor: [
          "#3da9fc", "#ef4565", "#ffa500", "#2ecc71", "#9966ff"
        ]
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
        title: {
          display: true,
          text: "Top 5 Riders Without Helmets"
        }
      }
    }
  });
}

// Load charts initially + refresh every 10s
loadCharts();
setInterval(loadCharts, 10000);