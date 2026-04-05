let analysisData = "";
let photosData = [];

// 사진 목록 로드
async function loadPhotos() {
  const res = await fetch("/api/photos");
  const photos = await res.json();
  photosData = photos;
  const grid = document.getElementById("photo-list");
  grid.innerHTML = photos.map(p => `<span class="photo-tag">${p}</span>`).join("");
}

// 분석
document.getElementById("btn-analyze").addEventListener("click", async () => {
  const btn = document.getElementById("btn-analyze");
  btn.disabled = true;
  btn.textContent = "분석 중...";

  const res = await fetch("/api/analyze", { method: "POST" });
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    btn.disabled = false;
    btn.textContent = "Claude로 분석 시작";
    return;
  }

  analysisData = data.analysis;
  document.getElementById("analysis-result").textContent = data.analysis;
  document.getElementById("step2").classList.remove("hidden");
  btn.textContent = "분석 완료";
});

// 자막 생성
document.getElementById("btn-generate").addEventListener("click", async () => {
  const btn = document.getElementById("btn-generate");
  btn.disabled = true;
  btn.textContent = "자막 생성 중...";

  const res = await fetch("/api/generate", {
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

  const list = document.getElementById("captions-list");
  list.innerHTML = data.captions.map((c, i) => `
    <div class="caption-item">
      <span class="caption-num">${i + 1}</span>
      <span class="caption-file">${data.photos[i]}</span>
      <input class="caption-input" data-index="${i}" value="${c}">
    </div>
  `).join("");

  document.getElementById("step3").classList.remove("hidden");
  btn.textContent = "자막 생성 완료";
});

// 영상 생성
document.getElementById("btn-make").addEventListener("click", async () => {
  const btn = document.getElementById("btn-make");
  btn.disabled = true;

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
  document.getElementById("progress-fill").style.width = "30%";
  pollProgress();
});

// 진행 상태 폴링
async function pollProgress() {
  const res = await fetch("/api/progress");
  const data = await res.json();

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

loadPhotos();
