// 햄버거 메뉴 토글
document.addEventListener("DOMContentLoaded", () => {
  const hamburger = document.getElementById("nav-hamburger");
  const mobileMenu = document.getElementById("nav-mobile-menu");
  if (hamburger && mobileMenu) {
    hamburger.addEventListener("click", () => {
      mobileMenu.classList.toggle("open");
    });
  }
});

let analysisData = "";
let photosData = [];
let contentType = (typeof window.TEMPLATE_ID !== "undefined" && window.TEMPLATE_ID) ? window.TEMPLATE_ID : "food";
let sortableInstance = null;
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

let step15Locked = false;

function lockStep15() {
  step15Locked = true;
  document.getElementById("btn-sort-time").style.display = "none";
  document.getElementById("btn-add-more").style.display = "none";
  document.getElementById("btn-to-step2").style.display = "none";
  document.querySelectorAll("#sort-zone .btn-delete").forEach(btn => {
    btn.style.display = "none";
  });
}

function unlockStep15() {
  step15Locked = false;
  document.getElementById("btn-sort-time").style.display = "";
  document.getElementById("btn-add-more").style.display = "";
  document.getElementById("btn-to-step2").style.display = "";
  document.querySelectorAll("#sort-zone .btn-delete").forEach(btn => {
    btn.style.display = "";
  });
}

function lockStep2() {
  document.getElementById("btn-generate").style.display = "none";
  document.getElementById("type-selector").classList.add("locked");
}

function unlockStep2() {
  document.getElementById("btn-generate").style.display = "";
  document.getElementById("btn-generate").disabled = false;
  document.getElementById("btn-generate").textContent = t("s2.generate");
  document.getElementById("type-selector").classList.remove("locked");
  setGenProgress(0);
}

function lockStep3() {
  document.getElementById("btn-make").style.display = "none";
}

function unlockStep3() {
  document.getElementById("btn-make").style.display = "";
  document.getElementById("btn-make").disabled = false;
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
  initSortable();
});

// ── 정렬 존 렌더링 ────────────────────────────────────

function initSortable() {
  const zone = document.getElementById("sort-zone");
  if (sortableInstance) sortableInstance.destroy();
  sortableInstance = Sortable.create(zone, {
    animation: 150,
    delay: 150,
    delayOnTouchOnly: true,
    touchStartThreshold: 5,
    swapThreshold: 0.3,
    ghostClass: "sort-ghost",
    chosenClass: "sort-chosen",
    onEnd() { updateOrderFromDOM(); }
  });
}

function renderSortZone() {
  const zone = document.getElementById("sort-zone");
  zone.innerHTML = "";
  photosData.forEach((name, i) => {
    const item = makeSortItem(name, i + 1);
    zone.appendChild(item);
  });
  if (step15Locked) {
    zone.querySelectorAll(".btn-delete").forEach(btn => btn.style.display = "none");
  }
  // step1-5가 보이는 상태일 때만 Sortable 초기화
  if (!document.getElementById("step1-5").classList.contains("hidden")) {
    initSortable();
  }
}

const VIDEO_EXTS = new Set([".mp4", ".mov", ".avi", ".m4v", ".mkv"]);
function isVideo(name) {
  return VIDEO_EXTS.has(name.slice(name.lastIndexOf(".")).toLowerCase());
}

function makeSortItem(name, num) {
  const div = document.createElement("div");
  div.className = "sort-item";
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
  lockStep15();
  document.getElementById("step2").classList.remove("hidden");
  document.getElementById("step2").scrollIntoView({ behavior: "smooth" }); updateStepNav();
});

// ── 자막 생성 진행 상태 바 ────────────────────────────

function setGenProgress(stage) {
  // stage: 0=숨김, 1=사진분석, 2=자막생성, 3=완료
  const prog = document.getElementById("generate-progress");
  if (!prog) return;
  if (stage === 0) { prog.classList.add("hidden"); return; }
  prog.classList.remove("hidden");

  const pcts = [0, 30, 65, 100];
  document.getElementById("gen-bar-fill").style.width = pcts[stage] + "%";

  [1, 2, 3].forEach(i => {
    const el = document.getElementById(`gstage-${i}`);
    el.classList.remove("active", "done");
    if (i === stage) el.classList.add("active");
    else if (i < stage) el.classList.add("done");
  });
}

// ── 자막 생성 (분석 → 생성 통합) ────────────────────

document.getElementById("btn-generate").addEventListener("click", async () => {
  const btn = document.getElementById("btn-generate");
  btn.disabled = true;

  try {
    // 현재 정렬 순서를 서버에 먼저 저장
    await fetch("/api/photos/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order: photosData })
    });

    setGenProgress(1);
    const analyzeRes = await fetch("/api/analyze", { method: "POST" });
    const analyzeData = await analyzeRes.json();
    if (analyzeData.error) {
      alert(analyzeData.error);
      setGenProgress(0);
      return;
    }
    analysisData = analyzeData.analysis;
    document.getElementById("analysis-result").textContent = analysisData;

    setGenProgress(2);
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

    setGenProgress(3);

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

    lockStep2();
    document.getElementById("step3").classList.remove("hidden");
    document.getElementById("step3").scrollIntoView({ behavior: "smooth" }); updateStepNav();

  } catch (err) {
    // 오류 발생 시 버튼 복구
    btn.disabled = false;
    btn.textContent = t("s2.generate");
    setGenProgress(0);
    alert("오류가 발생했어요: " + err.message);
  }
});

// ── 영상 생성 ─────────────────────────────────────────

document.getElementById("btn-make").addEventListener("click", async () => {
  lockStep3();
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
  if (data.status === "running") {
    document.getElementById("progress-msg").textContent = t("js.video_generating");
    document.getElementById("progress-fill").style.width = "70%";
    setTimeout(pollProgress, 2000);
  } else if (data.status === "done") {
    document.getElementById("progress-fill").style.width = "100%";
    document.getElementById("progress-msg").textContent = t("js.done");
    if (data.video_url) {
      const video = document.getElementById("result-video");
      video.src = data.video_url;
      const dlBtn = document.getElementById("btn-download");
      dlBtn.href = data.download_url || data.video_url;
      dlBtn.download = "reels.mp4";
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
  unlockStep15();
  unlockStep2();
  unlockStep3();
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
  document.getElementById("generate-progress").classList.add("hidden");
  document.getElementById("progress-fill").style.width = "0%";
  document.getElementById("progress-msg").textContent = "";
});

// ── 초기화 ────────────────────────────────────────────

async function init() {
  applyContentType(contentType);
  await loadPhotos();
}

init();
