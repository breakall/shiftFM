const scheduleList = document.getElementById("schedule-list");
const panel = document.getElementById("schedule-panel");
const openForm = document.getElementById("open-form");
const closeForm = document.getElementById("close-form");
const cancelForm = document.getElementById("cancel-form");
const scheduleForm = document.getElementById("schedule-form");
const panelTitle = document.getElementById("panel-title");
const dayPicker = document.getElementById("day-picker");
const recordForm = document.getElementById("record-form");
const configForm = document.getElementById("config-form");
const rssLink = document.getElementById("rss-link");
const copyRss = document.getElementById("copy-rss");
const settingsPanel = document.getElementById("settings-panel");
const openSettings = document.getElementById("open-settings");
const closeSettings = document.getElementById("close-settings");
const toggleRecordings = document.getElementById("toggle-recordings");
const recordingsList = document.getElementById("recordings-list");

let editingId = null;

const request = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const contentType = response.headers.get("Content-Type") || "";
  const data = contentType.includes("application/json") ? await response.json().catch(() => null) : null;
  if (!response.ok) {
    const message = data && data.error ? data.error : `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return data;
};

const openPanel = () => {
  panel.classList.add("open");
  panel.setAttribute("aria-hidden", "false");
};

const closePanel = () => {
  panel.classList.remove("open");
  panel.setAttribute("aria-hidden", "true");
  editingId = null;
  scheduleForm.reset();
  setDaySelection([]);
};

const openSettingsPanel = () => {
  settingsPanel.classList.add("open");
  settingsPanel.setAttribute("aria-hidden", "false");
};

const closeSettingsPanel = () => {
  settingsPanel.classList.remove("open");
  settingsPanel.setAttribute("aria-hidden", "true");
};


const setDaySelection = (days) => {
  const buttons = dayPicker.querySelectorAll("button");
  buttons.forEach((button) => {
    const day = button.dataset.day;
    button.classList.toggle("active", days.includes(day));
  });
};

const getDaySelection = () => {
  return Array.from(dayPicker.querySelectorAll("button"))
    .filter((button) => button.classList.contains("active"))
    .map((button) => button.dataset.day);
};

const renderSchedules = (schedules) => {
  scheduleList.innerHTML = "";
  if (!schedules.length) {
    const empty = document.createElement("div");
    empty.className = "card";
    empty.innerHTML = "<h3>No schedules yet</h3><p class='tagline'>Tap add to create your first recording.</p>";
    scheduleList.appendChild(empty);
    return;
  }

  schedules.forEach((schedule) => {
    const card = document.createElement("div");
    card.className = "card";
    const days = schedule.days && schedule.days.length ? schedule.days.join(", ") : "No days";
    const durationMin = Math.round(Number(schedule.duration_sec) / 60);
    card.innerHTML = `
      <h3>${schedule.name}</h3>
      <div class="meta">
        <span>${schedule.frequency_mhz} MHz</span>
        <span>${durationMin} min</span>
        <span>${schedule.start_time}</span>
        <span>${days}</span>
      </div>
      <div class="card-actions">
        <button class="toggle ${schedule.enabled ? "active" : ""}" data-action="toggle">${schedule.enabled ? "Enabled" : "Paused"}</button>
        <button class="ghost" data-action="edit">Edit</button>
        <button class="ghost" data-action="delete">Delete</button>
      </div>
    `;

    card.querySelector("[data-action='toggle']").addEventListener("click", async () => {
      await request(`/api/schedules/${schedule.id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !schedule.enabled }),
      });
      await loadSchedules();
    });

    card.querySelector("[data-action='edit']").addEventListener("click", () => {
      editingId = schedule.id;
      panelTitle.textContent = "Edit schedule";
      scheduleForm.name.value = schedule.name;
      scheduleForm.frequency_mhz.value = schedule.frequency_mhz;
      scheduleForm.duration_min.value = Math.round(Number(schedule.duration_sec) / 60);
      scheduleForm.start_time.value = schedule.start_time;
      setDaySelection(schedule.days || []);
      openPanel();
    });

    card.querySelector("[data-action='delete']").addEventListener("click", async () => {
      if (!confirm(`Delete ${schedule.name}?`)) {
        return;
      }
      await request(`/api/schedules/${schedule.id}`, { method: "DELETE" });
      await loadSchedules();
    });

    scheduleList.appendChild(card);
  });
};

const loadSchedules = async () => {
  const payload = await request("/api/schedules");
  renderSchedules(payload.schedules || []);
};

const loadConfig = async () => {
  const config = await request("/api/config");
  configForm.base_url.value = config.base_url || "";
  rssLink.textContent = `${(config.base_url || "").replace(/\/$/, "")}/rss.xml`;
};

const copyToClipboard = async (text) => {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const temp = document.createElement("input");
  temp.value = text;
  document.body.appendChild(temp);
  temp.select();
  document.execCommand("copy");
  temp.remove();
};

const parseFilename = (url) => {
  const name = (url || "").split("/").pop() || "";
  const cleaned = decodeURIComponent(name).replace(/\.mp3$/i, "");
  const parts = cleaned.split("_");
  if (parts.length < 3) {
    return { title: cleaned, frequency: "-", date: "-", timeRaw: "" };
  }
  const timeRaw = parts.pop();
  const date = parts.pop();
  const frequency = parts.pop();
  const title = parts.join(" ").replace(/-/g, " ");
  return { title, frequency, date, timeRaw };
};

const formatTime = (value) => {
  if (!/^\d{4}$/.test(value)) {
    return value || "-";
  }
  const hour = Number(value.slice(0, 2));
  const minute = value.slice(2);
  const period = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute} ${period}`;
};

const parseDuration = (value) => {
  if (!value) {
    return null;
  }
  const parts = value.split(":").map((part) => Number(part));
  if (parts.some((part) => Number.isNaN(part))) {
    return null;
  }
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }
  if (parts.length === 1) {
    return parts[0];
  }
  return null;
};

const formatTimeRange = (timeRaw, durationSec) => {
  const start = formatTime(timeRaw);
  if (!durationSec) {
    return { start, end: "-" };
  }
  if (!/^\d{4}$/.test(timeRaw)) {
    return { start, end: "-" };
  }
  const startHour = Number(timeRaw.slice(0, 2));
  const startMinute = Number(timeRaw.slice(2));
  const startTotal = startHour * 60 + startMinute;
  const endTotal = (startTotal + Math.round(durationSec / 60)) % (24 * 60);
  const endHour = Math.floor(endTotal / 60);
  const endMinute = endTotal % 60;
  const endLabel = formatTime(`${String(endHour).padStart(2, "0")}${String(endMinute).padStart(2, "0")}`);
  return { start, end: endLabel };
};

const renderRecordings = (items) => {
  recordingsList.innerHTML = "";
  if (!items.length) {
    recordingsList.innerHTML = "<div class='recordings-empty'>No recordings yet.</div>";
    return;
  }
  const table = document.createElement("div");
  table.className = "recordings-grid";
  table.innerHTML = `
    <div class="cell header">Show</div>
    <div class="cell header">Freq</div>
    <div class="cell header">Date</div>
    <div class="cell header start">Start</div>
    <div class="cell header end">End</div>
  `;

  items.forEach((item) => {
    const url = item.url || "#";
    const parsed = parseFilename(url);
    const timeRange = formatTimeRange(parsed.timeRaw, item.duration);
    table.insertAdjacentHTML(
      "beforeend",
      `
        <div class="cell"><a href="${url}" target="_blank" rel="noopener">${parsed.title}</a></div>
        <div class="cell">${parsed.frequency}</div>
        <div class="cell">${parsed.date}</div>
        <div class="cell start">${timeRange.start}</div>
        <div class="cell end">${timeRange.end}</div>
      `
    );
  });

  recordingsList.appendChild(table);
};


const loadRecordings = async () => {
  const response = await fetch("/rss.xml");
  if (!response.ok) {
    renderRecordings([]);
    return;
  }
  const text = await response.text();
  const doc = new DOMParser().parseFromString(text, "text/xml");
  const items = Array.from(doc.querySelectorAll("item")).map((item) => ({
    title: item.querySelector("title")?.textContent || "",
    pubDate: item.querySelector("pubDate")?.textContent || "",
    url: item.querySelector("enclosure")?.getAttribute("url") || "",
    duration: parseDuration(item.getElementsByTagName("itunes:duration")[0]?.textContent || ""),
  }));
  renderRecordings(items);
};

copyRss.addEventListener("click", async () => {
  const url = rssLink.textContent.trim();
  if (!url) {
    return;
  }
  try {
    await copyToClipboard(url);
    copyRss.textContent = "Copied!";
    setTimeout(() => {
      copyRss.textContent = "Copy RSS feed URL";
    }, 1500);
  } catch (error) {
    copyRss.textContent = "Copy failed";
    setTimeout(() => {
      copyRss.textContent = "Copy RSS feed URL";
    }, 1500);
  }
});

toggleRecordings.addEventListener("click", async () => {
  const isOpen = recordingsList.classList.toggle("open");
  recordingsList.setAttribute("aria-hidden", String(!isOpen));
  toggleRecordings.textContent = isOpen ? "Hide recordings" : "Show recordings";
  if (isOpen) {
    await loadRecordings();
  }
});

openForm.addEventListener("click", () => {
  panelTitle.textContent = "New schedule";
  scheduleForm.reset();
  setDaySelection([]);
  openPanel();
});

closeForm.addEventListener("click", closePanel);
cancelForm.addEventListener("click", closePanel);
openSettings.addEventListener("click", openSettingsPanel);
closeSettings.addEventListener("click", closeSettingsPanel);

dayPicker.querySelectorAll("button").forEach((button) => {
  button.addEventListener("click", () => {
    button.classList.toggle("active");
  });
});

scheduleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    name: scheduleForm.name.value.trim(),
    frequency_mhz: Number(scheduleForm.frequency_mhz.value),
    duration_sec: Number(scheduleForm.duration_min.value) * 60,
    start_time: scheduleForm.start_time.value,
    days: getDaySelection(),
    enabled: true,
  };

  try {
    if (editingId) {
      await request(`/api/schedules/${editingId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      await request("/api/schedules", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    closePanel();
    await loadSchedules();
  } catch (error) {
    alert(error.message);
  }
});

recordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    name: recordForm.name.value.trim(),
    frequency_mhz: Number(recordForm.frequency_mhz.value),
    duration_sec: Number(recordForm.duration_min.value) * 60,
  };
  try {
    await request("/api/record-now", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    recordForm.reset();
  } catch (error) {
    alert(error.message);
  }
});

configForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = { base_url: configForm.base_url.value.trim() };
  const config = await request("/api/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  rssLink.textContent = `${config.base_url.replace(/\/$/, "")}/rss.xml`;
});

loadSchedules();
loadConfig();
