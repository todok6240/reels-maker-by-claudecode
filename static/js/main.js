let analysisData = "";
let photosData = [];
let dragSrc = null;
let placeholder = null;
let contentType = "food";
let step1Locked = false;

function lockStep1() {
  step1Locked = true;
  document.getElementById("btn-clear-all").style.display = "none";
  document.getElementById("btn-next").style.display = "none";
  document.getElementById("drop-zone").classList.add("locked");
  updatePhotoTags();
}

function unlockStep1() {
  step1Locked = false;
  document.getElementById("btn-next").style.display = "";
  document.getElementById("drop-zone").classList.remove("locked");
  updatePhotoTags();
}

// ── 스텝 네비게이션 ───────────────────────────────────
const STEP_IDS = ["step1", "step1-5", "step2", "step3", "step4"];
let maxStepReached = 0;

function updateStepNav() {
  const navItems = document.querySelectorAll(".step-nav-item");
  const scrollY = window.scrollY + window.innerHeight / 2;

  let currentIdx = 0;
  STEP_IDS.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el || el.classList.contains("hidden")) return;
    const top = el.getBoundingClientRect().top + window.scrollY;
    if (top <= scrollY) currentIdx = i;
  });

  maxStepReached = Math.max(maxStepReached, currentIdx);

  navItems.forEach((item, i) => {
    const targetId = item.dataset.target;
    const el = document.getElementById(targetId);
    const visible = el && !el.classList.contains("hidden");
    item.classList.remove("is-active", "is-done");
    if (!visible) return;
    if (i < maxStepReached) item.classList.add("is-done");
    else if (i === maxStepReached) item.classList.add("is-active");
  });
}

document.querySelectorAll(".step-nav-item").forEach(item => {
  item.addEventListener("click", () => {
    const el = document.getElementById(item.dataset.target);
    if (el && !el.classList.contains("hidden")) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

window.addEventListener("scroll", updateStepNav);
updateStepNav();

// ── 언어 변경 시 동적 컨텐츠 재적용 ─────────────────
window.addEventListener("langchange", () => {
  applyContentType(contentType);
  const sortBtn = document.getElementById("btn-sort-time");
  if (sortBtn && !sortBtn.disabled) sortBtn.textContent = t("js.sort_time");
});

// ── 콘텐츠 유형 설정 ─────────────────────────────────
const CONTENT_TYPE_SHOW_PRICE = {
  food: true, travel: true, product: true, fitness: true, vlog: false
};

document.querySelectorAll(".type-card").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".type-card").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    contentType = btn.dataset.type;
    applyContentType(contentType);
  });
});

function applyContentType(type) {
  document.getElementById("label-name").textContent     = t(`ct.${type}.name`);
  document.getElementById("label-location").textContent = t(`ct.${type}.location`);
  document.getElementById("label-price").textContent    = t(`ct.${type}.price`);
  document.getElementById("label-review").textContent   = t(`ct.${type}.review`);
  document.getElementById("name").placeholder           = t(`ct.${type}.ph.name`);
  document.getElementById("location").placeholder      = t(`ct.${type}.ph.location`);
  document.getElementById("price").placeholder         = t(`ct.${type}.ph.price`);
  document.getElementById("review").placeholder        = t(`ct.${type}.ph.review`);
  document.getElementById("group-price").style.display = CONTENT_TYPE_SHOW_PRICE[type] ? "" : "none";
}

// ── 업로드 ────────────────────────────────────────────

const dropZone   = document.getElementById("drop-zone");
const fileInput  = document.getElementById("file-input");

dropZone.addEventListener("dragover", e => { if (step1Locked) return; e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => { if (step1Locked) return; e.preventDefault(); dropZone.classList.remove("drag-over"); uploadFiles(e.dataTransfer.files); });
fileInput.addEventListener("change", () => { if (step1Locked) return; uploadFiles(fileInput.files); });

async function uploadFiles(files) {
  if (!files.length) return;
  showUploadProgress(t("js.uploading", files.length), 30);

  const formData = new FormData();
  for (const f of files) formData.append("photos", f);

  const res  = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();

  showUploadProgress(t("js.uploaded", data.count), 100);
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
  if (photosData.length > 0) document.getElementById("btn-next").disabled = false;
  updatePhotoTags();
  renderSortZone();
}

// ── 다음 단계 버튼 ────────────────────────────────────

document.getElementById("btn-next").addEventListener("click", () => {
  lockStep1();
  document.getElementById("step1-5").classList.remove("hidden");
  document.getElementById("step1-5").scrollIntoView({ behavior: "smooth" }); updateStepNav();
});

// ── 정렬 존 렌더링 ────────────────────────────────────

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
    <button class="btn-delete" title="✕">✕</button>
  `;

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

  div.addEventListener("dragstart", e => {
    dragSrc = div;
    e.dataTransfer.effectAllowed = "move";

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
    photosData.map(p => `
      <span class="photo-tag">
        ${p}
        ${step1Locked ? "" : `<button class="photo-tag-del" data-name="${p}" title="✕">✕</button>`}
      </span>
    `).join("");

  if (!step1Locked) {
    document.querySelectorAll(".photo-tag-del").forEach(btn => {
      btn.addEventListener("click", async () => {
        const name = btn.dataset.name;
        await fetch("/api/photos/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: name })
        });
        photosData = photosData.filter(p => p !== name);
        updatePhotoTags();
        renderSortZone();
        if (photosData.length === 0) {
          document.getElementById("btn-next").disabled = true;
          document.getElementById("btn-clear-all").style.display = "none";
        }
      });
    });
  }

  document.getElementById("btn-clear-all").style.display = (!step1Locked && photosData.length > 0) ? "" : "none";
}

// ── 사진 추가 (오른쪽 끝) ─────────────────────────────

document.getElementById("file-input-more").addEventListener("change", async function () {
  if (!this.files.length) return;
  showUploadProgress(t("js.adding", this.files.length), 30);

  const formData = new FormData();
  for (const f of this.files) formData.append("photos", f);

  const res  = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();

  showUploadProgress(t("js.added", data.count), 100);

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
  btn.textContent = t("js.sorting");

  const res = await fetch("/api/photos/sort-by-time");
  const sorted = await res.json();

  photosData = sorted;
  renderSortZone();
  updatePhotoTags();

  btn.disabled = false;
  btn.textContent = t("js.sort_time");
});

// ── 1.5단계 → 2단계 이동 ─────────────────────────────

document.getElementById("btn-to-step2").addEventListener("click", () => {
  document.getElementById("step2").classList.remove("hidden");
  document.getElementById("step2").scrollIntoView({ behavior: "smooth" }); updateStepNav();
});

// ── 자막 생성 (분석 → 생성 통합) ────────────────────

document.getElementById("btn-generate").addEventListener("click", async () => {
  const btn = document.getElementById("btn-generate");
  btn.disabled = true;

  btn.textContent = t("js.analyzing");
  const analyzeRes = await fetch("/api/analyze", { method: "POST" });
  const analyzeData = await analyzeRes.json();
  if (analyzeData.error) {
    alert(analyzeData.error);
    btn.disabled = false;
    btn.textContent = t("s2.generate");
    return;
  }
  analysisData = analyzeData.analysis;
  document.getElementById("analysis-result").textContent = analysisData;

  btn.textContent = t("js.generating");
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name:         document.getElementById("name").value,
      location:     document.getElementById("location").value,
      price:        document.getElementById("price").value,
      review:       document.getElementById("review").value,
      analysis:     analysisData,
      content_type: contentType,
    })
  });
  const data = await res.json();

  const thumbSrc = name => isVideo(name)
    ? `/api/thumbnail/${encodeURIComponent(name)}`
    : `/api/photo/${encodeURIComponent(name)}`;

  document.getElementById("captions-list").innerHTML = data.captions.map((c, i) => `
    <div class="caption-item">
      <span class="caption-num">${i + 1}</span>
      <img class="caption-thumb" src="${thumbSrc(data.photos[i])}" alt="${data.photos[i]}">
      <input class="caption-input" data-index="${i}" value="${c}">
    </div>
  `).join("");

  document.getElementById("step3").classList.remove("hidden");
  document.getElementById("step3").scrollIntoView({ behavior: "smooth" }); updateStepNav();
  btn.textContent = t("js.generated");
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
      analysis:     analysisData,
      captions:     captions,
      content_type: contentType,
    })
  });

  document.getElementById("step4").classList.remove("hidden");
  document.getElementById("step4").scrollIntoView({ behavior: "smooth" }); updateStepNav();
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
    document.getElementById("progress-msg").textContent = t("js.done");
    if (data.video_url) {
      const video = document.getElementById("result-video");
      video.src = data.video_url;
      document.getElementById("btn-download").href = data.video_url;
      document.getElementById("result-box").classList.remove("hidden");
      document.getElementById("restart-wrap").classList.remove("hidden");
    }
  } else if (data.status === "error") {
    document.getElementById("progress-msg").textContent = t("js.error") + " " + data.message;
  }
}

// ── 처음부터 다시 시작하기 ───────────────────────────

document.getElementById("btn-restart").addEventListener("click", async () => {
  await fetch("/api/session/reset", { method: "POST" });
  maxStepReached = 0;
  photosData = [];
  unlockStep1();
  renderSortZone();
  updatePhotoTags();
  document.getElementById("btn-next").disabled = true;
  document.getElementById("result-box").classList.add("hidden");
  document.getElementById("restart-wrap").classList.add("hidden");
  document.getElementById("result-video").src = "";
  document.getElementById("progress-fill").style.width = "0%";
  document.getElementById("progress-msg").textContent = "";
  ["step1-5", "step2", "step3", "step4"].forEach(id =>
    document.getElementById(id).classList.add("hidden")
  );
  document.getElementById("step1").scrollIntoView({ behavior: "smooth" }); updateStepNav();
});

// ── 전체 삭제 ─────────────────────────────────────────

document.getElementById("btn-clear-all").addEventListener("click", async () => {
  if (!confirm(t("js.confirm_clear"))) return;
  await fetch("/api/session/reset", { method: "POST" });
  photosData = [];
  renderSortZone();
  updatePhotoTags();
  document.getElementById("btn-next").disabled = true;
  document.getElementById("btn-clear-all").style.display = "none";
  document.getElementById("step1-5").classList.add("hidden");
  document.getElementById("step2").classList.add("hidden");
  document.getElementById("step3").classList.add("hidden");
  document.getElementById("step4").classList.add("hidden");
});

// ── 초기화 ────────────────────────────────────────────

async function init() {
  applyContentType(contentType);
  await loadPhotos();
}

init();
