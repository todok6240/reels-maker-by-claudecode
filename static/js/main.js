let analysisData = "";
let photosData = [];
let dragSrc = null;
let placeholder = null;

// ── 업로드 ────────────────────────────────────────────

const dropZone   = document.getElementById("drop-zone");
const fileInput  = document.getElementById("file-input");

dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => { e.preventDefault(); dropZone.classList.remove("drag-over"); uploadFiles(e.dataTransfer.files); });
fileInput.addEventListener("change", () => uploadFiles(fileInput.files));

async function uploadFiles(files) {
  if (!files.length) return;
  showUploadProgress(`${files.length}장 업로드 중...`, 30);

  const formData = new FormData();
  for (const f of files) formData.append("photos", f);

  const res  = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();

  showUploadProgress(`✅ ${data.count}장 업로드 완료`, 100);
  await loadPhotos();
  document.getElementById("btn-next").disabled = false;
}

function showUploadProgress(msg, pct) {
  document.getElementById("upload-progress").classList.remove("hidden");
  document.getElementById("upload-fill").style.width = pct + "%";
  document.getElementById("upload-msg").textContent  = msg;
}

// ── 사진 목록 로드 ────────────────────────────────────

async function loadPhotos() {
  const res = await fetch("/api/photos");
  photosData = await res.json();
  const grid = document.getElementById("photo-list");
  grid.innerHTML = photosData.map(p => `<span class="photo-tag">${p}</span>`).join("");
  if (photosData.length > 0) document.getElementById("btn-next").disabled = false;
  renderSortZone();
}

// ── 다음 단계 버튼 ────────────────────────────────────

document.getElementById("btn-next").addEventListener("click", () => {
  document.getElementById("step1-5").classList.remove("hidden");
  document.getElementById("step1-5").scrollIntoView({ behavior: "smooth" });
});

// ── 정렬 존 렌더링 ────────────────────────────────────

// sort-zone 전체에서 dragover → placeholder 위치 실시간 이동
document.getElementById("sort-zone").addEventListener("dragover", e => {
  e.preventDefault();
  if (!dragSrc || !placeholder) return;

  const zone  = document.getElementById("sort-zone");
  const items = [...zone.querySelectorAll(".sort-item:not(.dragging)")];

  let inserted = false;
  for (const item of items) {
    const rect = item.getBoundingClientRect();
    if (e.clientX < rect.left + rect.width / 2) {
      zone.insertBefore(placeholder, item);
      inserted = true;
      break;
    }
  }
  if (!inserted) zone.appendChild(placeholder);
});

function renderSortZone() {
  const zone = document.getElementById("sort-zone");
  zone.innerHTML = "";
  photosData.forEach((name, i) => {
    const item = makeSortItem(name, i + 1);
    zone.appendChild(item);
  });
}

const VIDEO_EXTS = new Set([".mp4", ".mov", ".avi", ".m4v", ".mkv"]);
function isVideo(name) {
  return VIDEO_EXTS.has(name.slice(name.lastIndexOf(".")).toLowerCase());
}

function makeSortItem(name, num) {
  const div = document.createElement("div");
  div.className = "sort-item";
  div.draggable = true;
  div.dataset.name = name;

  const thumbSrc = isVideo(name)
    ? `/api/thumbnail/${encodeURIComponent(name)}`
    : `/api/photo/${encodeURIComponent(name)}`;

  div.innerHTML = `
    <img src="${thumbSrc}" alt="${name}">
    ${isVideo(name) ? '<div class="video-badge">▶</div>' : ""}
    <span class="sort-num">${num}</span>
    <button class="btn-delete" title="삭제">✕</button>
  `;

  // 삭제
  div.querySelector(".btn-delete").addEventListener("click", async () => {
    await fetch("/api/photos/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: name })
    });
    photosData = photosData.filter(p => p !== name);
    renderSortZone();
    updatePhotoTags();
  });

  // 드래그
  div.addEventListener("dragstart", e => {
    dragSrc = div;
    e.dataTransfer.effectAllowed = "move";

    // placeholder 생성 (드래그 중 빈 자리 표시)
    placeholder = document.createElement("div");
    placeholder.className = "sort-placeholder";
    placeholder.style.width  = div.offsetWidth  + "px";
    placeholder.style.height = div.offsetHeight + "px";

    setTimeout(() => div.classList.add("dragging"), 0);
  });

  div.addEventListener("dragend", () => {
    div.classList.remove("dragging");
    if (placeholder && placeholder.parentNode) {
      placeholder.parentNode.insertBefore(dragSrc, placeholder);
      placeholder.remove();
    }
    placeholder = null;
    dragSrc = null;
    updateOrderFromDOM();
  });

  return div;
}

function updateOrderFromDOM() {
  const items = [...document.querySelectorAll("#sort-zone .sort-item")];
  photosData = items.map(el => el.dataset.name);
  items.forEach((el, i) => { el.querySelector(".sort-num").textContent = i + 1; });
  updatePhotoTags();
}

function updatePhotoTags() {
  document.getElementById("photo-list").innerHTML =
    photosData.map(p => `<span class="photo-tag">${p}</span>`).join("");
}

// ── 사진 추가 (오른쪽 끝) ─────────────────────────────

document.getElementById("file-input-more").addEventListener("change", async function () {
  if (!this.files.length) return;
  showUploadProgress(`${this.files.length}장 추가 중...`, 30);

  const formData = new FormData();
  for (const f of this.files) formData.append("photos", f);

  const res  = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();

  showUploadProgress(`✅ ${data.count}장 추가 완료`, 100);

  // 기존 목록에 없는 것만 오른쪽 끝에 추가
  const zone = document.getElementById("sort-zone");
  data.uploaded.forEach(name => {
    if (!photosData.includes(name)) {
      photosData.push(name);
      zone.appendChild(makeSortItem(name, photosData.length));
    }
  });
  updatePhotoTags();
  this.value = "";
});

// ── 시간순 정렬 ───────────────────────────────────────

document.getElementById("btn-sort-time").addEventListener("click", async () => {
  const btn = document.getElementById("btn-sort-time");
  btn.disabled = true;
  btn.textContent = "정렬 중...";

  const res = await fetch("/api/photos/sort-by-time");
  const sorted = await res.json();

  photosData = sorted;
  renderSortZone();
  updatePhotoTags();

  btn.disabled = false;
  btn.textContent = "🕐 시간순 정렬";
});

// ── 분석 ─────────────────────────────────────────────

document.getElementById("btn-analyze").addEventListener("click", async () => {
  const btn = document.getElementById("btn-analyze");
  btn.disabled = true;
  btn.textContent = "분석 중...";

  const res  = await fetch("/api/analyze", { method: "POST" });
  const data = await res.json();
  if (data.error) { alert(data.error); btn.disabled = false; btn.textContent = "Claude로 분석 시작"; return; }

  analysisData = data.analysis;
  document.getElementById("analysis-result").textContent = data.analysis;
  document.getElementById("step2").classList.remove("hidden");
  document.getElementById("step2").scrollIntoView({ behavior: "smooth" });
  btn.textContent = "분석 완료";
});

// ── 자막 생성 ─────────────────────────────────────────

document.getElementById("btn-generate").addEventListener("click", async () => {
  const btn = document.getElementById("btn-generate");
  btn.disabled = true;
  btn.textContent = "자막 생성 중...";

  const res  = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name:     document.getElementById("name").value,
      location: document.getElementById("location").value,
      price:    document.getElementById("price").value,
      review:   document.getElementById("review").value,
      analysis: analysisData,
    })
  });
  const data = await res.json();

  document.getElementById("captions-list").innerHTML = data.captions.map((c, i) => `
    <div class="caption-item">
      <span class="caption-num">${i + 1}</span>
      <span class="caption-file">${data.photos[i]}</span>
      <input class="caption-input" data-index="${i}" value="${c}">
    </div>
  `).join("");

  document.getElementById("step3").classList.remove("hidden");
  document.getElementById("step3").scrollIntoView({ behavior: "smooth" });
  btn.textContent = "자막 생성 완료";
});

// ── 영상 생성 ─────────────────────────────────────────

document.getElementById("btn-make").addEventListener("click", async () => {
  document.getElementById("btn-make").disabled = true;
  const captions = [...document.querySelectorAll(".caption-input")].map(el => el.value);

  await fetch("/api/make", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name:     document.getElementById("name").value,
      location: document.getElementById("location").value,
      price:    document.getElementById("price").value,
      review:   document.getElementById("review").value,
      analysis: analysisData,
      captions: captions,
    })
  });

  document.getElementById("step4").classList.remove("hidden");
  document.getElementById("step4").scrollIntoView({ behavior: "smooth" });
  document.getElementById("progress-fill").style.width = "30%";
  pollProgress();
});

// ── 진행 폴링 ─────────────────────────────────────────

async function pollProgress() {
  const data = await (await fetch("/api/progress")).json();
  document.getElementById("progress-msg").textContent = data.message;
  if (data.status === "running") {
    document.getElementById("progress-fill").style.width = "70%";
    setTimeout(pollProgress, 2000);
  } else if (data.status === "done") {
    document.getElementById("progress-fill").style.width = "100%";
    document.getElementById("progress-msg").textContent = "✅ 완료! output 폴더에서 확인하세요.";
  } else if (data.status === "error") {
    document.getElementById("progress-msg").textContent = "❌ 오류: " + data.message;
  }
}

// ── 초기화 ────────────────────────────────────────────

// ── 이어서 진행 / 새 작업 시작 ───────────────────────

document.getElementById("btn-resume").addEventListener("click", async () => {
  document.getElementById("resume-banner").classList.add("hidden");
  await loadPhotos();
  document.getElementById("step1-5").classList.remove("hidden");
  document.getElementById("step1-5").scrollIntoView({ behavior: "smooth" });
});

document.getElementById("btn-reset").addEventListener("click", async () => {
  await fetch("/api/session/reset", { method: "POST" });
  document.getElementById("resume-banner").classList.add("hidden");
  photosData = [];
  renderSortZone();
  updatePhotoTags();
  document.getElementById("btn-next").disabled = true;
  document.getElementById("step1-5").classList.add("hidden");
  document.getElementById("step2").classList.add("hidden");
  document.getElementById("step3").classList.add("hidden");
  document.getElementById("step4").classList.add("hidden");
});

async function init() {
  const res  = await fetch("/api/session");
  const data = await res.json();

  if (data.status === "working" && data.photos.length > 0) {
    document.getElementById("resume-banner").classList.remove("hidden");
  } else {
    await loadPhotos();
  }
}

init();
