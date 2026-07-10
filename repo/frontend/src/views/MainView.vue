<template>
  <div class="main-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">NEMOFISH</div>
      </div>
      
      <div class="header-center">
        <div class="view-switcher">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: $t('main.layoutGraph'), split: $t('main.layoutSplit'), workbench: $t('main.layoutWorkbench') }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <LanguageSwitcher />
        <div class="step-divider"></div>
        <div class="workflow-step">
          <span class="step-num">Step {{ currentStep }}/5</span>
          <span class="step-name">{{ $tm('main.stepNames')[currentStep - 1] }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel 
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="currentPhase"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step Components -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <!-- Step 1: 图谱构建 -->
        <Step1GraphBuild 
          v-if="currentStep === 1"
          :currentPhase="currentPhase"
          :projectData="projectData"
          :ontologyProgress="ontologyProgress"
          :buildProgress="buildProgress"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @next-step="handleNextStep"
        />
        <!-- Step 2: 环境搭建 -->
        <Step2EnvSetup
          v-else-if="currentStep === 2"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GraphPanel from '../components/GraphPanel.vue'
import Step1GraphBuild from '../components/Step1GraphBuild.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { generateOntology, getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const route = useRoute()
const router = useRouter()
const { t, tm } = useI18n()

// Layout State
const viewMode = ref('split') // graph | split | workbench

// Step State
const currentStep = ref(1) // 1: 图谱构建, 2: 环境搭建, 3: 开始模拟, 4: 报告生成, 5: 深度互动
const stepNames = computed(() => tm('main.stepNames'))

// Data State
const currentProjectId = ref(route.params.projectId)
const loading = ref(false)
const graphLoading = ref(false)
const error = ref('')
const projectData = ref(null)
const graphData = ref(null)
const currentPhase = ref(-1) // -1: Upload, 0: Ontology, 1: Build, 2: Complete
const ontologyProgress = ref(null)
const buildProgress = ref(null)
const systemLogs = ref([])

// Polling timers
let pollTimer = null
let graphPollTimer = null

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  if (error.value) return 'error'
  if (currentPhase.value >= 2) return 'completed'
  return 'processing'
})

const statusText = computed(() => {
  if (error.value) return t('uiMain.statusError')
  if (currentPhase.value >= 2) return t('uiMain.statusReady')
  if (currentPhase.value === 1) return t('uiMain.statusBuildingGraph')
  if (currentPhase.value === 0) return t('uiMain.statusGeneratingOntology')
  return t('uiMain.statusInitializing')
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  // Keep last 100 logs
  if (systemLogs.value.length > 100) {
    systemLogs.value.shift()
  }
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

const handleNextStep = (params = {}) => {
  if (currentStep.value < 5) {
    currentStep.value++
    addLog(t('log.enterStep', { step: currentStep.value, name: stepNames.value[currentStep.value - 1] }))
    
    // 如果是从 Step 2 进入 Step 3，记录模拟轮数配置
    if (currentStep.value === 3 && params.maxRounds) {
      addLog(t('log.customSimRounds', { rounds: params.maxRounds }))
    }
  }
}

const handleGoBack = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    addLog(t('log.returnToStep', { step: currentStep.value, name: stepNames.value[currentStep.value - 1] }))
  }
}

// --- Data Logic ---

const initProject = async () => {
  addLog(t('uiMain.logProjectViewInit'))
  if (currentProjectId.value === 'new') {
    await handleNewProject()
  } else {
    await loadProject()
  }
}

const handleNewProject = async () => {
  const pending = getPendingUpload()
  if (!pending.isPending || pending.files.length === 0) {
    error.value = t('uiMain.errNoPendingFiles')
    addLog(t('uiMain.logNoPendingFiles'))
    return
  }

  try {
    loading.value = true
    currentPhase.value = 0
    ontologyProgress.value = { message: t('uiMain.uploadingAnalyzingDocs') }
    addLog(t('uiMain.logStartOntologyUpload'))

    const formData = new FormData()
    pending.files.forEach(f => formData.append('files', f))
    formData.append('simulation_requirement', pending.simulationRequirement)

    const res = await generateOntology(formData)
    if (res.success) {
      clearPendingUpload()
      currentProjectId.value = res.data.project_id
      projectData.value = res.data

      router.replace({ name: 'Process', params: { projectId: res.data.project_id } })
      ontologyProgress.value = null
      addLog(t('uiMain.logOntologySuccess', { id: res.data.project_id }))
      await startBuildGraph()
    } else {
      error.value = res.error || t('uiMain.errOntologyGenFailed')
      addLog(t('uiMain.logErrGeneratingOntology', { error: error.value }))
    }
  } catch (err) {
    error.value = err.message
    addLog(t('uiMain.logExceptionNewProject', { error: err.message }))
  } finally {
    loading.value = false
  }
}

const loadProject = async () => {
  try {
    loading.value = true
    addLog(t('uiMain.logLoadingProject', { id: currentProjectId.value }))
    const res = await getProject(currentProjectId.value)
    if (res.success) {
      projectData.value = res.data
      updatePhaseByStatus(res.data.status)
      addLog(t('uiMain.logProjectLoaded', { status: res.data.status }))

      if (res.data.status === 'ontology_generated' && !res.data.graph_id) {
        await startBuildGraph()
      } else if (res.data.status === 'graph_building' && res.data.graph_build_task_id) {
        currentPhase.value = 1
        startPollingTask(res.data.graph_build_task_id)
        startGraphPolling()
      } else if (res.data.status === 'graph_completed' && res.data.graph_id) {
        currentPhase.value = 2
        await loadGraph(res.data.graph_id)
      }
    } else {
      error.value = res.error
      addLog(t('uiMain.logErrLoadingProject', { error: res.error }))
    }
  } catch (err) {
    error.value = err.message
    addLog(t('uiMain.logExceptionLoadProject', { error: err.message }))
  } finally {
    loading.value = false
  }
}

const updatePhaseByStatus = (status) => {
  switch (status) {
    case 'created':
    case 'ontology_generated': currentPhase.value = 0; break;
    case 'graph_building': currentPhase.value = 1; break;
    case 'graph_completed': currentPhase.value = 2; break;
    case 'failed': error.value = t('uiMain.errProjectFailed'); break;
  }
}

const startBuildGraph = async () => {
  try {
    currentPhase.value = 1
    buildProgress.value = { progress: 0, message: t('uiMain.startingBuild') }
    addLog(t('uiMain.logInitiatingBuild'))

    const res = await buildGraph({ project_id: currentProjectId.value })
    if (res.success) {
      addLog(t('uiMain.logBuildTaskStarted', { taskId: res.data.task_id }))
      startGraphPolling()
      startPollingTask(res.data.task_id)
    } else {
      error.value = res.error
      addLog(t('uiMain.logErrStartingBuild', { error: res.error }))
    }
  } catch (err) {
    error.value = err.message
    addLog(t('uiMain.logExceptionStartBuild', { error: err.message }))
  }
}

const startGraphPolling = () => {
  addLog(t('uiMain.logStartedPollingGraph'))
  fetchGraphData()
  graphPollTimer = setInterval(fetchGraphData, 10000)
}

const fetchGraphData = async () => {
  try {
    // Refresh project info to check for graph_id
    const projRes = await getProject(currentProjectId.value)
    if (projRes.success && projRes.data.graph_id) {
      const gRes = await getGraphData(projRes.data.graph_id)
      if (gRes.success) {
        graphData.value = gRes.data
        const nodeCount = gRes.data.node_count || gRes.data.nodes?.length || 0
        const edgeCount = gRes.data.edge_count || gRes.data.edges?.length || 0
        addLog(t('uiMain.logGraphRefreshed', { nodes: nodeCount, edges: edgeCount }))
      }
    }
  } catch (err) {
    console.warn('Graph fetch error:', err)
  }
}

const startPollingTask = (taskId) => {
  pollTaskStatus(taskId)
  pollTimer = setInterval(() => pollTaskStatus(taskId), 2000)
}

const pollTaskStatus = async (taskId) => {
  try {
    const res = await getTaskStatus(taskId)
    if (res.success) {
      const task = res.data
      
      // Log progress message if it changed
      if (task.message && task.message !== buildProgress.value?.message) {
        addLog(task.message)
      }
      
      buildProgress.value = { progress: task.progress || 0, message: task.message }
      
      if (task.status === 'completed') {
        addLog(t('uiMain.logBuildTaskCompleted'))
        stopPolling()
        stopGraphPolling() // Stop polling, do final load
        currentPhase.value = 2

        // Final load
        const projRes = await getProject(currentProjectId.value)
        if (projRes.success && projRes.data.graph_id) {
            projectData.value = projRes.data
            await loadGraph(projRes.data.graph_id)
        }
      } else if (task.status === 'failed') {
        stopPolling()
        error.value = task.error
        addLog(t('uiMain.logBuildTaskFailed', { error: task.error }))
      }
    }
  } catch (e) {
    console.error(e)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  addLog(t('uiMain.logLoadingFullGraph', { id: graphId }))
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog(t('uiMain.logGraphLoadedSuccess'))
    } else {
      addLog(t('uiMain.logGraphLoadFailed', { error: res.error }))
    }
  } catch (e) {
    addLog(t('uiMain.logExceptionLoadingGraph', { error: e.message }))
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    addLog(t('uiMain.logManualGraphRefresh'))
    loadGraph(projectData.value.graph_id)
  }
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const stopGraphPolling = () => {
  if (graphPollTimer) {
    clearInterval(graphPollTimer)
    graphPollTimer = null
    addLog(t('uiMain.logGraphPollingStopped'))
  }
}

onMounted(() => {
  initProject()
})

onUnmounted(() => {
  stopPolling()
  stopGraphPolling()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-1);
  overflow: hidden;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
}

/* Header — deep navy chrome (AWS top nav) */
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

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-label);
  color: var(--nav-ink-inactive);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-body);
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--nav-ink-inactive);
}

.step-name {
  font-weight: 700;
  color: var(--nav-ink);
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: var(--nav-bg-2);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--nav-ink-inactive);
}

.status-indicator.processing .dot { background: var(--status-provisioning); animation: pulse 1s infinite; }
.status-indicator.completed .dot { background: var(--status-running); }
.status-indicator.error .dot { background: var(--status-stopped); }

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
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
  transition: width var(--motion-base) var(--motion-easing), opacity var(--motion-base) var(--motion-easing), transform var(--motion-base) var(--motion-easing);
  will-change: width, opacity, transform;
}

.panel-wrapper.left {
  border-right: 1px solid var(--border);
}
</style>
