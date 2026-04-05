// i18n.js — 다국어 지원 (한국어 / English / 日本語)

const TRANSLATIONS = {
  ko: {
    // Nav
    'nav.history': '과거 생성 히스토리',
    'nav.settings': '⚙️ 설정',
    'nav.logout': '로그아웃',

    // Login
    'login.subtitle': '사진으로 릴스를 자동으로 만들어보세요',
    'login.google': 'Google로 로그인',
    'login.or': '또는',
    'login.guest': '게스트로 시작하기',
    'login.notice': '게스트 로그인은 브라우저를 닫으면 기록이 사라져요',

    // Step nav
    'step.1': '사진 업로드',
    'step.2': '순서 조정',
    'step.3': '정보 입력',
    'step.4': '자막 확인',
    'step.5': '영상 생성',

    // Step 1
    's1.title': '1단계 — 사진 업로드',
    's1.drop_title': '사진을 드래그하거나 클릭해서 업로드',
    's1.drop_sub': 'JPG, PNG, MP4, MOV 여러 파일 가능',
    's1.clear': '전체 삭제',
    's1.next': '다음 단계 →',

    // Step 1.5
    's15.title': '1.5단계 — 사진 순서 조정',
    's15.desc': '드래그로 순서를 바꾸거나 삭제할 수 있어요. 추가 사진은 오른쪽 끝에 붙어요.',
    's15.add': '+ 사진 추가',
    's15.sort_time': '🕐 시간순 정렬',
    's15.next': '다음 단계 →',

    // Step 2
    's2.title': '2단계 — 정보 입력',
    's2.generate': '자막 생성',
    'type.food': '맛집/카페',
    'type.travel': '여행/관광',
    'type.product': '상품 리뷰',
    'type.fitness': '운동/헬스',
    'type.vlog': '일상/브이로그',

    // Step 3
    's3.title': '3단계 — 자막 확인 & 영상 생성',
    's3.analysis': 'Claude 분석 결과 보기',
    's3.make': '영상 생성 시작',

    // Step 4
    's4.title': '영상 생성 중...',
    's4.download': '다운로드',
    's4.restart': '처음부터 다시 시작하기',

    // History
    'hist.title': '과거 생성 히스토리',
    'hist.th.title': '타이틀',
    'hist.th.location': '위치',
    'hist.th.price': '가격대',
    'hist.th.photos': '사진 수',
    'hist.th.date': '생성일',
    'hist.th.download': '다운로드',
    'hist.empty': '아직 생성된 릴스가 없어요.',
    'hist.download': '다운로드',

    // Settings
    'set.title': '환경설정',
    'set.color_title': '퍼스널 컬러',
    'set.color_desc': '버튼, 강조 색상 등 앱 전체의 메인 컬러를 바꿀 수 있어요.',
    'set.custom': '직접 선택',
    'set.save': '저장',
    'set.reset': '기본값으로',
    'set.saved': '저장되었어요!',
    'set.reset_msg': '기본값으로 초기화했어요.',

    // JS dynamic
    'js.uploading': (n) => `${n}장 업로드 중...`,
    'js.uploaded': (n) => `✅ ${n}장 업로드 완료`,
    'js.adding': (n) => `${n}장 추가 중...`,
    'js.added': (n) => `✅ ${n}장 추가 완료`,
    'js.sorting': '정렬 중...',
    'js.sort_time': '🕐 시간순 정렬',
    'js.analyzing': '사진 분석 중...',
    'js.generating': '자막 생성 중...',
    'js.generated': '자막 생성 완료 ✓',
    'js.confirm_clear': '업로드한 파일을 모두 삭제할까요?',
    'js.done': '✅ 완료!',
    'js.error': '❌ 오류:',

    // Content type fields
    'ct.food.name': '가게 이름',       'ct.food.location': '위치',     'ct.food.price': '가격대',     'ct.food.review': '총평',
    'ct.food.ph.name': '예: 두동 쭈꾸미', 'ct.food.ph.location': '예: 서울 용두동', 'ct.food.ph.price': '예: 1인 12,000원', 'ct.food.ph.review': '예: 불맛 가득한 쭈꾸미 맛집',
    'ct.travel.name': '장소명',         'ct.travel.location': '위치',   'ct.travel.price': '입장료',   'ct.travel.review': '총평',
    'ct.travel.ph.name': '예: 경복궁',  'ct.travel.ph.location': '예: 서울 종로구', 'ct.travel.ph.price': '예: 무료 / 3,000원', 'ct.travel.ph.review': '예: 야경이 아름다운 서울 대표 궁궐',
    'ct.product.name': '상품명',        'ct.product.location': '구매처', 'ct.product.price': '가격',    'ct.product.review': '총평',
    'ct.product.ph.name': '예: 에어팟 프로 2', 'ct.product.ph.location': '예: 애플 공식몰', 'ct.product.ph.price': '예: 329,000원', 'ct.product.ph.review': '예: 노이즈 캔슬링 압도적으로 좋아요',
    'ct.fitness.name': '운동 종목/장소', 'ct.fitness.location': '위치',  'ct.fitness.price': '이용 요금', 'ct.fitness.review': '총평',
    'ct.fitness.ph.name': '예: 크로스핏 강남점', 'ct.fitness.ph.location': '예: 서울 강남구', 'ct.fitness.ph.price': '예: 월 99,000원', 'ct.fitness.ph.review': '예: 체계적인 코치진이 인상적이에요',
    'ct.vlog.name': '제목',             'ct.vlog.location': '장소',     'ct.vlog.price': '',           'ct.vlog.review': '내용 요약',
    'ct.vlog.ph.name': '예: 제주 2박3일 브이로그', 'ct.vlog.ph.location': '예: 제주도', 'ct.vlog.ph.price': '', 'ct.vlog.ph.review': '예: 올레길 트레킹부터 흑돼지까지',
  },

  en: {
    'nav.history': 'History',
    'nav.settings': '⚙️ Settings',
    'nav.logout': 'Logout',

    'login.subtitle': 'Create reels from your photos automatically',
    'login.google': 'Sign in with Google',
    'login.or': 'or',
    'login.guest': 'Continue as Guest',
    'login.notice': 'Guest sessions are cleared when you close the browser',

    'step.1': 'Upload',
    'step.2': 'Reorder',
    'step.3': 'Info',
    'step.4': 'Captions',
    'step.5': 'Generate',

    's1.title': 'Step 1 — Upload Photos',
    's1.drop_title': 'Drag & drop or click to upload',
    's1.drop_sub': 'JPG, PNG, MP4, MOV — multiple files supported',
    's1.clear': 'Clear All',
    's1.next': 'Next →',

    's15.title': 'Step 1.5 — Reorder Photos',
    's15.desc': 'Drag to reorder or delete. New photos are added at the end.',
    's15.add': '+ Add Photos',
    's15.sort_time': '🕐 Sort by Time',
    's15.next': 'Next →',

    's2.title': 'Step 2 — Enter Info',
    's2.generate': 'Generate Captions',
    'type.food': 'Restaurant',
    'type.travel': 'Travel',
    'type.product': 'Product',
    'type.fitness': 'Fitness',
    'type.vlog': 'Vlog',

    's3.title': 'Step 3 — Check Captions',
    's3.analysis': 'View Claude Analysis',
    's3.make': 'Generate Video',

    's4.title': 'Generating video...',
    's4.download': 'Download',
    's4.restart': 'Start Over',

    'hist.title': 'Generation History',
    'hist.th.title': 'Title',
    'hist.th.location': 'Location',
    'hist.th.price': 'Price',
    'hist.th.photos': 'Photos',
    'hist.th.date': 'Created',
    'hist.th.download': 'Download',
    'hist.empty': 'No reels generated yet.',
    'hist.download': 'Download',

    'set.title': 'Settings',
    'set.color_title': 'Theme Color',
    'set.color_desc': 'Change the main accent color used throughout the app.',
    'set.custom': 'Custom',
    'set.save': 'Save',
    'set.reset': 'Reset to Default',
    'set.saved': 'Saved!',
    'set.reset_msg': 'Reset to default.',

    'js.uploading': (n) => `Uploading ${n} file${n > 1 ? 's' : ''}...`,
    'js.uploaded': (n) => `✅ ${n} file${n > 1 ? 's' : ''} uploaded`,
    'js.adding': (n) => `Adding ${n} file${n > 1 ? 's' : ''}...`,
    'js.added': (n) => `✅ ${n} file${n > 1 ? 's' : ''} added`,
    'js.sorting': 'Sorting...',
    'js.sort_time': '🕐 Sort by Time',
    'js.analyzing': 'Analyzing photos...',
    'js.generating': 'Generating captions...',
    'js.generated': 'Captions ready ✓',
    'js.confirm_clear': 'Delete all uploaded files?',
    'js.done': '✅ Done!',
    'js.error': '❌ Error:',

    'ct.food.name': 'Place Name',      'ct.food.location': 'Location',     'ct.food.price': 'Price Range', 'ct.food.review': 'Review',
    'ct.food.ph.name': "e.g. Joe's Ramen", 'ct.food.ph.location': 'e.g. New York', 'ct.food.ph.price': 'e.g. $15/person', 'ct.food.ph.review': 'e.g. Amazing broth, must visit!',
    'ct.travel.name': 'Place Name',    'ct.travel.location': 'Location',   'ct.travel.price': 'Entrance Fee', 'ct.travel.review': 'Review',
    'ct.travel.ph.name': 'e.g. Eiffel Tower', 'ct.travel.ph.location': 'e.g. Paris, France', 'ct.travel.ph.price': 'e.g. Free / $25', 'ct.travel.ph.review': 'e.g. Iconic landmark, stunning views',
    'ct.product.name': 'Product Name', 'ct.product.location': 'Where to Buy', 'ct.product.price': 'Price', 'ct.product.review': 'Review',
    'ct.product.ph.name': 'e.g. AirPods Pro 2', 'ct.product.ph.location': 'e.g. Apple Store', 'ct.product.ph.price': 'e.g. $249', 'ct.product.ph.review': 'e.g. Amazing noise cancellation!',
    'ct.fitness.name': 'Workout / Place', 'ct.fitness.location': 'Location', 'ct.fitness.price': 'Fee', 'ct.fitness.review': 'Review',
    'ct.fitness.ph.name': 'e.g. CrossFit Downtown', 'ct.fitness.ph.location': 'e.g. Los Angeles, CA', 'ct.fitness.ph.price': 'e.g. $120/month', 'ct.fitness.ph.review': 'e.g. Great coaching, highly recommend',
    'ct.vlog.name': 'Title',           'ct.vlog.location': 'Location',     'ct.vlog.price': '',           'ct.vlog.review': 'Summary',
    'ct.vlog.ph.name': 'e.g. 3-Day Jeju Trip Vlog', 'ct.vlog.ph.location': 'e.g. Jeju Island', 'ct.vlog.ph.price': '', 'ct.vlog.ph.review': 'e.g. Hiking trails to local food',
  },

  ja: {
    'nav.history': '過去の生成履歴',
    'nav.settings': '⚙️ 設定',
    'nav.logout': 'ログアウト',

    'login.subtitle': '写真からリールを自動で作成しましょう',
    'login.google': 'Googleでログイン',
    'login.or': 'または',
    'login.guest': 'ゲストとして始める',
    'login.notice': 'ゲストセッションはブラウザを閉じると消えます',

    'step.1': 'アップロード',
    'step.2': '並び替え',
    'step.3': '情報入力',
    'step.4': '字幕確認',
    'step.5': '動画生成',

    's1.title': 'ステップ1 — 写真アップロード',
    's1.drop_title': 'ドラッグ&ドロップまたはクリックしてアップロード',
    's1.drop_sub': 'JPG、PNG、MP4、MOV 複数ファイル対応',
    's1.clear': 'すべて削除',
    's1.next': '次へ →',

    's15.title': 'ステップ1.5 — 順番の変更',
    's15.desc': 'ドラッグで並び替えや削除ができます。追加した写真は末尾に追加されます。',
    's15.add': '+ 写真を追加',
    's15.sort_time': '🕐 時間順に並べ替え',
    's15.next': '次へ →',

    's2.title': 'ステップ2 — 情報入力',
    's2.generate': '字幕を生成',
    'type.food': 'グルメ/カフェ',
    'type.travel': '旅行/観光',
    'type.product': '商品レビュー',
    'type.fitness': 'フィットネス',
    'type.vlog': '日常/Vlog',

    's3.title': 'ステップ3 — 字幕確認',
    's3.analysis': 'Claude分析結果を見る',
    's3.make': '動画生成を開始',

    's4.title': '動画生成中...',
    's4.download': 'ダウンロード',
    's4.restart': '最初からやり直す',

    'hist.title': '過去の生成履歴',
    'hist.th.title': 'タイトル',
    'hist.th.location': '場所',
    'hist.th.price': '価格帯',
    'hist.th.photos': '写真数',
    'hist.th.date': '作成日',
    'hist.th.download': 'ダウンロード',
    'hist.empty': 'まだリールがありません。',
    'hist.download': 'ダウンロード',

    'set.title': '設定',
    'set.color_title': 'テーマカラー',
    'set.color_desc': 'ボタンや強調色などアプリ全体のカラーを変更できます。',
    'set.custom': 'カスタム',
    'set.save': '保存',
    'set.reset': 'デフォルトに戻す',
    'set.saved': '保存しました！',
    'set.reset_msg': 'デフォルトに戻しました。',

    'js.uploading': (n) => `${n}枚アップロード中...`,
    'js.uploaded': (n) => `✅ ${n}枚アップロード完了`,
    'js.adding': (n) => `${n}枚追加中...`,
    'js.added': (n) => `✅ ${n}枚追加完了`,
    'js.sorting': 'ソート中...',
    'js.sort_time': '🕐 時間順に並べ替え',
    'js.analyzing': '写真を分析中...',
    'js.generating': '字幕生成中...',
    'js.generated': '字幕生成完了 ✓',
    'js.confirm_clear': 'アップロードしたファイルをすべて削除しますか？',
    'js.done': '✅ 完了！',
    'js.error': '❌ エラー:',

    'ct.food.name': '店名',             'ct.food.location': '場所',         'ct.food.price': '価格帯',     'ct.food.review': '総評',
    'ct.food.ph.name': '例: 博多ラーメン一蘭', 'ct.food.ph.location': '例: 福岡市博多区', 'ct.food.ph.price': '例: 1人 1,000円', 'ct.food.ph.review': '例: 濃厚スープが絶品のラーメン店',
    'ct.travel.name': 'スポット名',      'ct.travel.location': '場所',       'ct.travel.price': '入場料',   'ct.travel.review': '総評',
    'ct.travel.ph.name': '例: 浅草寺',  'ct.travel.ph.location': '例: 東京都台東区', 'ct.travel.ph.price': '例: 無料', 'ct.travel.ph.review': '例: 東京を代表する観光スポット',
    'ct.product.name': '商品名',         'ct.product.location': '購入場所',  'ct.product.price': '価格',    'ct.product.review': '総評',
    'ct.product.ph.name': '例: AirPods Pro 2', 'ct.product.ph.location': '例: Apple Store', 'ct.product.ph.price': '例: 39,800円', 'ct.product.ph.review': '例: ノイキャンが最高です',
    'ct.fitness.name': '種目/場所',      'ct.fitness.location': '場所',      'ct.fitness.price': '料金',    'ct.fitness.review': '総評',
    'ct.fitness.ph.name': '例: クロスフィット渋谷', 'ct.fitness.ph.location': '例: 東京都渋谷区', 'ct.fitness.ph.price': '例: 月額 9,000円', 'ct.fitness.ph.review': '例: コーチが丁寧で初心者にも最適',
    'ct.vlog.name': 'タイトル',          'ct.vlog.location': '場所',         'ct.vlog.price': '',           'ct.vlog.review': '内容まとめ',
    'ct.vlog.ph.name': '例: 済州島 2泊3日 Vlog', 'ct.vlog.ph.location': '例: 済州島', 'ct.vlog.ph.price': '', 'ct.vlog.ph.review': '例: トレッキングからグルメまで',
  }
};

const SUPPORTED_LANGS = ['ko', 'en', 'ja'];

function detectLang() {
  const saved = localStorage.getItem('lang');
  if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
  const browser = (navigator.language || 'ko').slice(0, 2).toLowerCase();
  return SUPPORTED_LANGS.includes(browser) ? browser : 'ko';
}

let _currentLang = detectLang();

function t(key, arg) {
  const val = TRANSLATIONS[_currentLang]?.[key] ?? TRANSLATIONS['ko']?.[key] ?? key;
  return typeof val === 'function' ? val(arg) : val;
}

function applyTranslations() {
  document.documentElement.lang = _currentLang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  _updateSwitcherUI();
  window.dispatchEvent(new CustomEvent('langchange', { detail: { lang: _currentLang } }));
}

function _updateSwitcherUI() {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === _currentLang);
  });
}

function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) return;
  _currentLang = lang;
  localStorage.setItem('lang', lang);
  applyTranslations();
}

window.t = t;
window.setLang = setLang;
window.currentLang = () => _currentLang;

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => setLang(btn.dataset.lang));
  });
  applyTranslations();
});
