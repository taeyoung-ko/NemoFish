<template>
  <div class="home-container">
    <!-- ===== 인트로: 시스템 설명 페이지 ===== -->
    <template v-if="stage === 'intro'">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand">NEMOFISH</div>
      <div class="nav-links">
        <LanguageSwitcher />
        <a href="https://github.com/taeyoung-ko/NemoFish" target="_blank" class="github-link">
          {{ $t('nav.visitGithub') }} <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- 上半部分：Hero 区域 -->
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="version-text">{{ $t('home.version') }}</span>
          </div>
          
          <h1 class="main-title">
            {{ $t('home.heroTitle1') }}<br>
            <span class="gradient-text">{{ $t('home.heroTitle2') }}</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              <i18n-t keypath="home.heroDesc" tag="span">
                <template #brand><span class="highlight-bold">{{ $t('home.heroDescBrand') }}</span></template>
              </i18n-t>
            </p>
          </div>
           
          <div class="decoration-square"></div>
        </div>
        
        <div class="hero-right">
          <!-- Logo 区域 -->
          <div class="logo-container">
            <img src="../assets/logo/nemofish.png" alt="NemoFish Logo" class="hero-logo" />
          </div>
          
          <button class="scroll-down-btn" @click="scrollToBottom">
            ↓
          </button>
        </div>
      </section>

      <!-- 下半部分：双栏布局 -->
      <section class="dashboard-section">
        <!-- 左栏：状态与步骤 -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> {{ $t('home.systemStatus') }}
          </div>
          
          <h2 class="section-title">{{ $t('home.systemReady') }}</h2>
          <p class="section-desc">
            {{ $t('home.systemReadyDesc') }}
          </p>
          
          <!-- 项目模拟步骤介绍 (新增区域) -->
          <div class="steps-container">
            <div class="steps-header">
               <span class="diamond-icon">◇</span> {{ $t('home.workflowSequence') }}
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step01Title') }}</div>
                  <div class="step-desc">{{ $t('home.step01Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step02Title') }}</div>
                  <div class="step-desc">{{ $t('home.step02Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step03Title') }}</div>
                  <div class="step-desc">{{ $t('home.step03Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step04Title') }}</div>
                  <div class="step-desc">{{ $t('home.step04Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">05</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step05Title') }}</div>
                  <div class="step-desc">{{ $t('home.step05Desc') }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 시작하기 → 셋업 단계로 -->
        <div class="intro-cta">
          <button class="start-engine-btn intro-start-btn" @click="stage = 'setup'">
            <span>{{ $t('home.beginSetup') }}</span>
            <span class="btn-arrow">→</span>
          </button>
        </div>
      </section>

      <!-- 历史项目数据库 -->
      <HistoryDatabase />
      </div>
    </template>

    <!-- ===== 셋업: 뒤 페이지와 동일한 풀스크린 레이아웃 ===== -->
    <template v-else>
    <div class="setup-view">
      <!-- Header: 브랜드 · 중앙 뷰스위처 · 우측 -->
      <header class="app-header">
        <div class="header-left">
          <div class="brand" @click="stage = 'intro'">NEMOFISH</div>
        </div>
        <div class="header-center">
          <div class="view-switcher" v-if="designdb.available">
            <button v-for="mode in ['input', 'split', 'search']" :key="mode"
                    class="switch-btn" :class="{ active: setupView === mode }"
                    @click="setupView = mode">
              {{ { input: $t('home.viewInput'), split: $t('home.viewSplit'), search: $t('home.viewSearch') }[mode] }}
            </button>
          </div>
        </div>
        <div class="header-right">
          <LanguageSwitcher />
          <button class="setup-back" @click="stage = 'intro'">← {{ $t('home.back') }}</button>
        </div>
      </header>

      <!-- 동적 분할 (뒤 페이지 content-area와 동일) -->
      <main class="content-area">
        <!-- 좌: 입력 -->
        <div class="panel-wrapper left" :style="setupLeftStyle">
          <div class="setup-panel-inner">
              <!-- 上传区域 -->
              <div class="console-section">
                <div class="console-header">
                  <span class="console-label">{{ $t('home.realitySeed') }}</span>
                  <span class="console-meta">{{ $t('home.supportedFormats') }}</span>
                </div>
                <div
                  class="upload-zone"
                  :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                  @dragover.prevent="handleDragOver"
                  @dragleave.prevent="handleDragLeave"
                  @drop.prevent="handleDrop"
                  @click="triggerFileInput"
                >
                  <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt"
                         @change="handleFileSelect" style="display: none" :disabled="loading" />
                  <div v-if="files.length === 0" class="upload-placeholder">
                    <div class="upload-icon">↑</div>
                    <div class="upload-title">{{ $t('home.dragToUpload') }}</div>
                    <div class="upload-hint">{{ $t('home.orBrowse') }}</div>
                  </div>
                  <div v-else class="file-list">
                    <div v-for="(file, index) in files" :key="index" class="file-item">
                      <span class="file-icon">📄</span>
                      <span class="file-name">{{ file.name }}</span>
                      <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 输入区域 (프롬프트) -->
              <div class="console-section">
                <div class="console-header">
                  <span class="console-label">{{ $t('home.simulationPrompt') }}</span>
                </div>
                <div class="input-wrapper">
                  <textarea v-model="formData.simulationRequirement" class="code-input"
                            :placeholder="$t('home.promptPlaceholder')" rows="6" :disabled="loading"></textarea>
                  <div class="model-badge">{{ $t('home.engineBadge') }}</div>
                </div>
              </div>

              <!-- 선택된 배경자료 (선택한 것만) -->
              <div class="console-section" v-if="designdb.available">
                <div class="console-header">
                  <span class="console-label">{{ $t('home.designdbSelectedTitle') }}</span>
                  <span class="dd-selected">{{ $t('home.designdbSelected', { n: designdb.selectedIds.length }) }}</span>
                </div>
                <div class="dd-selected-list">
                  <p v-if="!selectedList.length" class="dd-empty">{{ $t('home.designdbNoneSelected') }}</p>
                  <div v-for="a in selectedList" :key="a.id" class="dd-sel-item"
                       @mouseenter="hoverArticle(a.id)" @mouseleave="closeDetail">
                    <div class="dd-sel-info">
                      <span class="dd-sel-title">{{ a.title }}</span>
                      <span class="dd-sel-cat">{{ a.category_name }}</span>
                    </div>
                    <button class="dd-sel-remove" @click.stop="toggleSelect(a.id)" @mouseenter.stop>×</button>
                  </div>
                </div>
              </div>

              <!-- 启动按钮 -->
              <div class="console-section btn-section">
                <button class="start-engine-btn" @click="startSimulation" :disabled="!canSubmit || loading">
                  <span v-if="loading">{{ $t('home.initializing') }}</span>
                  <span v-else>{{ $t('home.startEngine') }}</span>
                  <span class="btn-arrow">→</span>
                </button>
              </div>
            </div>
          </div>

          <!-- 우: designdb 검색결과 (클릭=선택/해제, hover=전문) -->
          <div class="panel-wrapper right" :style="setupRightStyle" v-if="designdb.available">
            <div class="setup-panel-inner">
              <div class="console-section">
                <div class="console-header">
                  <span class="console-label">{{ $t('home.viewSearch') }}</span>
                  <span class="dd-selected" v-if="designdb.selectedIds.length">
                    {{ $t('home.designdbSelected', { n: designdb.selectedIds.length }) }}
                  </span>
                </div>
                <!-- 검색 소스: 문서별(각 문서 = 다른 검색결과) + 수동 검색어 -->
                <div class="dd-sources" v-if="designdb.docSources.length">
                  <button class="dd-source" :class="{ active: designdb.activeSource === 'manual' }"
                          @click="selectSource('manual')">{{ $t('home.designdbSourceManual') }}</button>
                  <button v-for="(dsrc, i) in designdb.docSources" :key="i"
                          class="dd-source" :class="{ active: designdb.activeSource === i }"
                          @click="selectSource(i)">{{ dsrc.name }}</button>
                </div>
                <!-- 검색어 입력칸 (수동) -->
                <input class="dd-extra-input" v-model="designdb.query" @input="onManualInput"
                       :placeholder="$t('home.designdbManualPlaceholder')" :disabled="loading" />
                <button class="dd-search-btn dd-search-btn-full" @click="runDesigndbSearch"
                        :disabled="loading || designdb.searching || !effectiveQuery.trim()">
                  {{ designdb.searching ? $t('home.designdbSearching') : $t('home.designdbSearch') }}
                </button>
                <div class="dd-tabs">
                  <button v-for="tab in designdbTabs" :key="tab.id" class="dd-tab"
                          :class="{ active: designdb.activeTab === tab.id }"
                          @click="selectDesigndbTab(tab.id)">{{ tab.name }}</button>
                </div>
                <div class="dd-results">
                  <p v-if="!designdb.searched" class="dd-empty">{{ $t('home.designdbHint') }}</p>
                  <p v-else-if="designdb.searching" class="dd-empty">{{ $t('home.designdbSearching') }}</p>
                  <p v-else-if="!designdbResults.length" class="dd-empty">{{ $t('home.designdbNoResult') }}</p>
                  <div v-for="r in designdbResults" :key="r.id" class="dd-item"
                       :class="{ selected: designdb.selectedIds.includes(r.id) }"
                       @click="toggleSelect(r.id)"
                       @mouseenter="hoverArticle(r.id)" @mouseleave="closeDetail">
                    <div class="dd-item-title">{{ r.title }}<span class="dd-score">{{ (r.score * 100).toFixed(0) }}</span></div>
                    <div class="dd-item-meta">[{{ r.category_name }}] {{ r.field }} · {{ r.date }}</div>
                    <div class="dd-item-snippet">{{ r.snippet }}</div>
                  </div>
                </div>
                <!-- 페이지네이션 (전량을 페이지로 나눠 열람) -->
                <div class="dd-pagination" v-if="designdb.searched && designdb.total > designdb.pageSize">
                  <button class="dd-page-btn" @click="goToPage(designdb.page - 1)"
                          :disabled="designdb.page <= 1 || designdb.searching">‹</button>
                  <span class="dd-page-info">{{ designdb.page }} / {{ totalPages }}
                    <span class="dd-page-total">({{ $t('home.designdbTotal', { n: designdb.total }) }})</span>
                  </span>
                  <button class="dd-page-btn" @click="goToPage(designdb.page + 1)"
                          :disabled="designdb.page >= totalPages || designdb.searching">›</button>
                </div>
              </div>
            </div>
          </div>
      </main>
    </div>
    </template>

    <!-- hover 시 전문 미리보기 (페르소나 모달과 동일 패턴) -->
    <DesigndbArticleModal :open="designdb.detailOpen" :article="designdb.detailArticle"
                          :loading="designdb.detailLoading" @close="closeDetail" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import DesigndbArticleModal from '../components/DesigndbArticleModal.vue'

const router = useRouter()
const { t } = useI18n()

// 화면 단계: intro(시스템 설명) → setup(업로드·검색·입력)
const stage = ref('intro')

// 셋업 화면 뷰: input(입력만) | split(분할) | search(검색만) — 뒤 페이지 동적분할과 동일
const setupView = ref('split')
const setupLeftStyle = computed(() => {
  if (setupView.value === 'input') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (setupView.value === 'search') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})
const setupRightStyle = computed(() => {
  if (setupView.value === 'search') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (setupView.value === 'input') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// 表单数据
const formData = ref({
  simulationRequirement: ''
})

// 文件列表
const files = ref([])

// 状态
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)

// 文件输入引用
const fileInput = ref(null)

// LLM 준비상태 (백엔드 헬스체크용)
const llmReady = ref(false)
let llmTimer = null
const checkLlm = async () => {
  try {
    const r = await fetch('/api/llm/status')
    const d = await r.json()
    llmReady.value = !!d.llm_ready
  } catch (e) {
    llmReady.value = false
  }
}
// designdb 인덱스 상태 확인
const checkDesigndb = async () => {
  try {
    const r = await fetch('/api/designdb/status')
    const d = await r.json()
    designdb.available = !!d.available && d.count > 0
    designdb.categories = d.categories || []
  } catch (e) {
    designdb.available = false
  }
}
onMounted(() => {
  checkLlm()
  llmTimer = setInterval(checkLlm, 4000)
  checkDesigndb()
})
onUnmounted(() => {
  if (llmTimer) clearInterval(llmTimer)
})

// 计算属性:是否可以提交 (클라우드 키는 .env에서 로드 → 프롬프트+파일만 있으면 제출 가능)
const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

// ── designdb 배경자료 검색/선별 ──
const designdb = reactive({
  available: false,
  categories: [],       // [{id, name}]
  query: '',              // 수동 검색어 입력칸
  docSources: [],         // [{name, text}] 업로드 문서별 검색 소스
  activeSource: 'manual', // 'manual' | 문서 인덱스 — 활성 소스로만 검색
  searching: false,
  searched: false,
  activeTab: 'all',
  results: [],          // 현재 페이지 결과
  total: 0,             // 범위 내 전체 건수
  page: 1,
  pageSize: 20,
  known: {},            // id → 결과 요약(선택 목록 표시용)
  selectedIds: [],
  // hover 전문 미리보기 모달
  detailOpen: false,
  detailArticle: null,
  detailLoading: false
})

// 선택된 배경자료 목록(좌측 패널 표시용) — 선택한 것만
const selectedList = computed(() =>
  designdb.selectedIds.map(id => designdb.known[id]).filter(Boolean)
)

// 클릭 → 선택/해제
const toggleSelect = (id) => {
  const i = designdb.selectedIds.indexOf(id)
  if (i >= 0) designdb.selectedIds.splice(i, 1)
  else designdb.selectedIds.push(id)
}

// hover → (지연 후) 전문 모달. 곧바로 안 뜨고 잠깐 기다렸다 뜸.
const HOVER_DELAY = 450
let _hoverToken = 0
let _hoverTimer = null
const hoverArticle = (id) => {
  clearTimeout(_hoverTimer)
  _hoverTimer = setTimeout(() => doHoverFetch(id), HOVER_DELAY)
}
const doHoverFetch = async (id) => {
  const token = ++_hoverToken
  designdb.detailOpen = true
  designdb.detailLoading = true
  designdb.detailArticle = null
  try {
    const r = await fetch(`/api/designdb/article/${id}`)
    const d = await r.json()
    if (token === _hoverToken) designdb.detailArticle = d.success ? d.article : null
  } catch (e) {
    if (token === _hoverToken) designdb.detailArticle = null
  } finally {
    if (token === _hoverToken) designdb.detailLoading = false
  }
}
const closeDetail = () => {
  clearTimeout(_hoverTimer)
  _hoverToken++
  designdb.detailOpen = false
  designdb.detailArticle = null
}

// 탭: 전체 + 카테고리
const designdbTabs = computed(() => [
  { id: 'all', name: t('home.designdbTabAll') },
  ...designdb.categories.map(c => ({ id: c.id, name: c.name }))
])
const designdbResults = computed(() => designdb.results)
const totalPages = computed(() => Math.max(1, Math.ceil(designdb.total / designdb.pageSize)))
// 활성 소스(수동 검색어 or 특정 문서)의 검색어
const effectiveQuery = computed(() => {
  if (designdb.activeSource === 'manual') return designdb.query.trim()
  const d = designdb.docSources[designdb.activeSource]
  return d ? d.text.trim() : ''
})

// 업로드된 txt/md 문서를 각각 검색 소스로 등록 (pdf는 클라이언트에서 본문 못 읽음)
const extractDocs = async () => {
  const arr = []
  for (const f of files.value) {
    const ext = f.name.split('.').pop().toLowerCase()
    if (ext === 'txt' || ext === 'md') {
      try { arr.push({ name: f.name, text: (await f.text()).slice(0, 8000) }) } catch (e) { /* 무시 */ }
    }
  }
  designdb.docSources = arr
  // 첫 문서를 자동 선택하고 검색
  if (arr.length) selectSource(0)
}

// 소스 선택(문서 인덱스 or 'manual') → 그 소스로 검색(선택은 유지)
const selectSource = (src) => {
  designdb.activeSource = src
  if (effectiveQuery.value.trim()) runDesigndbSearch()
}

// 수동 검색어 입력 → manual 소스로 전환 후 디바운스 검색
let _searchDebounce = null
const onManualInput = () => {
  designdb.activeSource = 'manual'
  clearTimeout(_searchDebounce)
  _searchDebounce = setTimeout(() => { if (designdb.query.trim()) runDesigndbSearch() }, 700)
}

// (tab, page) 단위로 검색결과 조회. 전량을 랭킹해 페이지로 잘라 받음.
const fetchDesigndbPage = async (tabId, page) => {
  designdb.searching = true
  designdb.activeTab = tabId
  designdb.page = page
  try {
    const res = await fetch('/api/designdb/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: effectiveQuery.value,
        category: tabId === 'all' ? null : tabId,
        page,
        page_size: designdb.pageSize
      })
    })
    const d = await res.json()
    designdb.results = d.success ? (d.results || []) : []
    designdb.total = d.success ? (d.total || 0) : 0
    for (const r of designdb.results) designdb.known[r.id] = r
  } catch (e) {
    designdb.results = []
    designdb.total = 0
  } finally {
    designdb.searching = false
  }
}

const runDesigndbSearch = async () => {
  if (!effectiveQuery.value.trim()) return
  designdb.searched = true       // 선택(selectedIds)은 유지 — 초기화 안 함
  await fetchDesigndbPage('all', 1)
}

const selectDesigndbTab = async (tabId) => {
  await fetchDesigndbPage(tabId, 1)
}

const goToPage = async (p) => {
  if (p < 1 || p > totalPages.value || p === designdb.page) return
  await fetchDesigndbPage(designdb.activeTab, p)
}

// 触发文件选择
const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

// 处理文件选择
const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

// 处理拖拽相关
const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (e) => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

// 添加文件
const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
  extractDocs()   // 업로드 문서를 각각 검색 소스로 등록 + 자동 검색
}

// 移除文件
const removeFile = (index) => {
  files.value.splice(index, 1)
}

// 滚动到底部
const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

// 开始模拟 - 立即跳转，API调用在Process页面进行
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  // 存储待上传的数据 (designdb 선택 기사 id 포함)
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, designdb.selectedIds.slice())

    // 立即跳转到Process页面（使用特殊标识表示新建项目）
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
/* 색/폰트/반경/그림자는 전역 :root 토큰(design-tokens.css)을 사용한다 */

.home-container {
  min-height: 100vh;
  background: var(--canvas-subdued);
  font-family: var(--font-sans);
  color: var(--ink);
}

/* 顶部导航 */
.navbar {
  height: 60px;
  background: var(--nav-bg);
  color: var(--nav-ink);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}

.nav-brand {
  font-family: var(--font-sans);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 16px;
}

.github-link {
  color: var(--nav-ink);
  text-decoration: none;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity var(--motion-base);
}

.github-link:hover {
  opacity: 0.8;
}

.arrow {
  font-family: var(--font-sans);
}

/* 主要内容区 */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Hero 区域 */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
}

.orange-tag {
  background: var(--primary);
  color: var(--on-primary);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: var(--fs-label);
  border-radius: var(--radius-sm);
}

.version-text {
  color: var(--ink-subdued);
  font-weight: 500;
  letter-spacing: 0.5px;
}

.main-title {
  font-size: 4.5rem;
  line-height: 1.2;
  font-weight: 500;
  margin: 0 0 40px 0;
  letter-spacing: -2px;
  color: var(--ink);
}

.gradient-text {
  color: var(--ink);
  display: inline-block;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--ink-muted);
  max-width: 640px;
  margin-bottom: 50px;
  font-weight: 400;
  text-align: justify;
}

.hero-desc p {
  margin-bottom: 1.5rem;
}

.highlight-bold {
  color: var(--ink);
  font-weight: 700;
}

.highlight-orange {
  color: var(--link);
  font-weight: 700;
  font-family: var(--font-sans);
}

.highlight-code {
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--ink);
  font-weight: 600;
}

.slogan-text {
  font-size: 1.2rem;
  font-weight: 520;
  color: var(--ink);
  letter-spacing: 1px;
  border-left: 3px solid var(--primary);
  padding-left: 15px;
  margin-top: 20px;
}

.blinking-cursor {
  color: var(--link);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.decoration-square {
  width: 16px;
  height: 16px;
  background: var(--primary);
}

.hero-right {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
}

.logo-container {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  padding-right: 40px;
}

.hero-logo {
  max-width: 500px; /* 调整logo大小 */
  width: 100%;
}

.scroll-down-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--link);
  font-size: 1.2rem;
  transition: all var(--motion-base);
}

.scroll-down-btn:hover {
  border-color: var(--primary);
  background: var(--primary-tint);
}

/* Dashboard 双栏布局 */
.dashboard-section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-8);
  border-top: 1px solid var(--border);
  padding-top: var(--sp-8);
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
}

/* 상단 인트로(워크플로우) */
.left-panel {
  width: 100%;
}

.panel-header {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  color: var(--status-running);
  font-size: 0.8rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 520;
  margin: 0 0 15px 0;
  color: var(--ink);
}

.section-desc {
  color: var(--ink-muted);
  margin-bottom: 25px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-card);
  padding: 20px 30px;
  min-width: 150px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: var(--fs-display);
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 5px;
}

.metric-label {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
}

/* 项目模拟步骤介绍 */
.steps-container {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-card);
  padding: 30px;
  position: relative;
}

.steps-header {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--ink-muted);
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.workflow-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--sp-5);
}

.workflow-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sp-2);
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--ink-subdued);
}

.step-info {
  flex: 1;
}

.step-title {
  font-weight: 600;
  font-size: var(--fs-section);
  color: var(--ink);
  margin-bottom: 4px;
}

.step-desc {
  font-size: var(--fs-body);
  color: var(--ink-muted);
}

/* 交互控制台 (전체폭) */
.right-panel {
  width: 100%;
}

/* 인트로 → 셋업 진입 버튼 */
.intro-cta {
  display: flex;
  justify-content: center;
  margin-top: var(--sp-6);
}
.intro-start-btn {
  width: auto;
  min-width: 240px;
}

/* ===== 셋업 = 뒤 페이지(MainView)와 동일한 풀스크린 레이아웃 ===== */
.setup-view {
  position: fixed;
  inset: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-1);
  overflow: hidden;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  z-index: 50;
}
.app-header {
  height: 56px;
  border-bottom: 1px solid var(--nav-bg-2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-6);
  background: var(--nav-bg);
  z-index: 100;
  position: relative;
  flex-shrink: 0;
}
.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}
.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
.brand {
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.5px;
  color: var(--nav-ink);
  cursor: pointer;
}
.setup-back {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--nav-ink-inactive);
  background: transparent;
  border: 1px solid var(--nav-bg-2);
  border-radius: var(--radius-md);
  padding: var(--sp-2) var(--sp-3);
  cursor: pointer;
  transition: color var(--motion-base) var(--motion-easing);
}
.setup-back:hover { color: var(--nav-ink); }

/* 뷰 스위처 (뒤 페이지와 동일) */
.view-switcher {
  display: flex;
  background: var(--nav-bg-2);
  padding: 4px;
  border-radius: var(--radius-md);
  gap: 4px;
}
.switch-btn {
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  padding: 6px var(--sp-4);
  font-size: var(--fs-label);
  font-weight: 600;
  color: var(--nav-ink-inactive);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--motion-base);
}
.switch-btn.active {
  background: var(--nav-bg);
  border-bottom-color: var(--nav-active);
  color: var(--nav-ink);
}

/* content-area (뒤 페이지와 동일 — 전체폭 동적 분할) */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  background: var(--canvas-subdued);
}
.panel-wrapper {
  height: 100%;
  overflow: hidden;
  background: var(--surface-1);
  transition: width var(--motion-base) var(--motion-easing),
              opacity var(--motion-base) var(--motion-easing),
              transform var(--motion-base) var(--motion-easing);
  will-change: width, opacity, transform;
}
.panel-wrapper.left {
  border-right: 1px solid var(--border);
}
.setup-panel-inner {
  height: 100%;
  overflow-y: auto;
  padding: var(--sp-5);
}
.dd-selected-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin-top: var(--sp-2);
}
.dd-sel-item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--primary-tint);
}
.dd-sel-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.dd-sel-title {
  font-size: var(--fs-label); font-weight: 600; color: var(--ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dd-sel-cat { font-size: var(--fs-label); color: var(--ink-muted); }
.dd-sel-remove {
  border: none; background: transparent; color: var(--ink-subdued);
  font-size: 18px; line-height: 1; cursor: pointer; padding: 0 var(--sp-1); flex-shrink: 0;
}
.dd-sel-remove:hover { color: var(--ink); }

.console-box {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-card);
  padding: 8px; /* 内边距形成双重边框感 */
}

.console-section {
  padding: 20px;
}

.console-section.btn-section {
  padding-top: 0;
}

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--ink-muted);
}

.upload-zone {
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--motion-base);
  background: var(--surface-2);
}

.upload-zone.has-files {
  align-items: flex-start;
}

.upload-zone:hover {
  background: var(--border-subtle);
  border-color: var(--ink-subdued);
}

.upload-zone.drag-over {
  background: var(--primary-tint);
  border-color: var(--primary);
}

.upload-placeholder {
  text-align: center;
}

.upload-icon {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  color: var(--ink-subdued);
}

.upload-title {
  font-weight: 500;
  font-size: var(--fs-body);
  color: var(--ink);
  margin-bottom: 5px;
}

.upload-hint {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--ink-subdued);
}

.file-list {
  width: 100%;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-item {
  display: flex;
  align-items: center;
  background: var(--surface-1);
  padding: 8px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-body);
}

.file-name {
  flex: 1;
  margin: 0 10px;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: var(--ink-subdued);
  transition: color var(--motion-fast);
}

.remove-btn:hover {
  color: var(--status-stopped);
}

.console-divider {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
}

.console-divider span {
  padding: 0 15px;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--ink-subdued);
  letter-spacing: 1px;
}

.input-wrapper {
  position: relative;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-2);
  transition: border-color var(--motion-fast);
}

.input-wrapper:focus-within {
  border-color: var(--link);
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: var(--fs-body);
  color: var(--ink);
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 15px;
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  color: var(--ink-subdued);
}

/* ===== designdb 배경자료 검색 (DESIGN.md 토큰 준수) ===== */
.dd-selected {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  font-weight: 600;
}
.dd-hint {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
  margin: var(--sp-1) 0 var(--sp-3);
  line-height: 1.5;
}
/* 검색 소스 선택(수동 + 문서별) */
.dd-sources {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-bottom: var(--sp-3);
}
.dd-source {
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: var(--surface-1);
  color: var(--ink-muted);
  font-size: var(--fs-label);
  cursor: pointer;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all var(--motion-base) var(--motion-easing);
}
.dd-source:hover { border-color: var(--border-strong); }
.dd-source.active {
  border-color: var(--ink);
  background: var(--primary-tint);
  color: var(--ink);
  font-weight: 600;
}
/* 수동 검색어 입력칸 */
.dd-extra-input {
  width: 100%;
  padding: var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  outline: none;
  transition: border-color var(--motion-base) var(--motion-easing);
}
.dd-extra-input:focus { border-color: var(--border-strong); }
.dd-search-btn-full { width: 100%; margin-top: var(--sp-2); }
.dd-search-btn {
  padding: var(--sp-2) var(--sp-4);
  border: none;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: var(--on-primary);
  box-shadow: var(--shadow-button-inset);
  font-size: var(--fs-label);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity var(--motion-fast) var(--motion-easing);
}
.dd-search-btn:hover:not(:disabled) { opacity: 0.85; }
.dd-search-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.dd-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-top: var(--sp-4);
}
.dd-tab {
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: var(--surface-1);
  color: var(--ink-muted);
  font-size: var(--fs-label);
  cursor: pointer;
  transition: all var(--motion-base) var(--motion-easing);
}
.dd-tab:hover { border-color: var(--border-strong); }
.dd-tab.active {
  border-color: var(--ink);
  background: var(--primary-tint);
  color: var(--ink);
  font-weight: 600;
}

/* 좌우분할 (뒤 단계 좌우패널과 동일한 결) */
.dd-results {
  margin-top: var(--sp-4);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}
/* 페이지네이션 */
.dd-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-4);
  margin-top: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--border-subtle);
}
.dd-page-btn {
  min-width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  color: var(--ink);
  font-size: var(--fs-body);
  cursor: pointer;
  transition: border-color var(--motion-base) var(--motion-easing);
}
.dd-page-btn:hover:not(:disabled) { border-color: var(--border-strong); }
.dd-page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.dd-page-info { font-size: var(--fs-label); color: var(--ink-muted); }
.dd-page-total { color: var(--ink-subdued); }
.dd-empty {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
  padding: var(--sp-4);
  text-align: center;
}
/* 결과 카드 — 클릭=선택/해제, hover=전문 모달 (체크박스 없음) */
.dd-item {
  padding: var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  cursor: pointer;
  transition: border-color var(--motion-base) var(--motion-easing),
              background var(--motion-base) var(--motion-easing);
}
.dd-item:hover { border-color: var(--border-strong); }
.dd-item.selected { border-color: var(--ink); background: var(--primary-tint); }
.dd-item-title {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--ink);
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}
.dd-score {
  font-size: var(--fs-label);
  font-family: var(--font-mono);
  color: var(--ink-muted);
  background: var(--surface-2);
  padding: 1px var(--sp-2);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  margin-left: auto;
}
.dd-item-meta {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  margin-top: var(--sp-1);
}
.dd-item-snippet {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
  margin-top: var(--sp-1);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.start-engine-btn {
  width: 100%;
  background: var(--primary);
  color: var(--on-primary);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  padding: 20px;
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 1.05rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all var(--motion-base) var(--motion-easing);
  letter-spacing: 0.02em;
  position: relative;
  overflow: hidden;
}

/* 可点击状态（非禁用） */
.start-engine-btn:not(:disabled) {
  background: var(--primary);
  border: 1px solid var(--primary);
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: var(--surface-2);
  color: var(--ink-subdued);
  cursor: not-allowed;
  transform: none;
  border: 1px solid var(--border);
}

/* 引导动画：미묘한 오렌지 보더 펄스 */
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(255, 153, 0, 0.35); }
  70% { box-shadow: 0 0 0 6px rgba(255, 153, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 153, 0, 0); }
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .dashboard-section {
    flex-direction: column;
  }
  
  .hero-section {
    flex-direction: column;
  }
  
  .hero-left {
    padding-right: 0;
    margin-bottom: 40px;
  }
  
  .hero-logo {
    max-width: 200px;
    margin-bottom: 20px;
  }
}
</style>

<style>
/* English locale adjustments (unscoped to target html[lang]) */
html[lang="en"] .main-title {
  font-size: 3.5rem;
  font-family: var(--font-sans);
  letter-spacing: -1px;
}

html[lang="en"] .hero-desc {
  text-align: left;
  font-family: var(--font-sans);
  letter-spacing: 0;
}

html[lang="en"] .slogan-text {
  font-family: var(--font-sans);
  letter-spacing: 0;
}

html[lang="en"] .tag-row {
  font-family: var(--font-sans);
}

html[lang="en"] .navbar .nav-links {
  font-family: var(--font-sans);
}

/* Left pane: system status + workflow */
html[lang="en"] .status-section {
  font-family: var(--font-sans);
}

html[lang="en"] .status-section .status-ready {
  font-size: 1.6rem;
}

html[lang="en"] .status-section .metric-value {
  font-family: var(--font-mono);
  font-size: 1.4rem;
}

html[lang="en"] .workflow-list .step-title {
  font-family: var(--font-sans);
}

html[lang="en"] .workflow-list .step-desc {
  font-family: var(--font-sans) !important;
  font-size: 0.72rem !important;
  line-height: 1.4 !important;
}

html[lang="en"] .workflow-list {
  font-family: var(--font-sans);
}
</style>
