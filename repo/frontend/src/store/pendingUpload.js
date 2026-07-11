/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  designdbIds: [],      // designdb에서 선별한 시드 기사 id 목록
  isPending: false
})

export function setPendingUpload(files, requirement, designdbIds = []) {
  state.files = files
  state.simulationRequirement = requirement
  state.designdbIds = designdbIds
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    designdbIds: state.designdbIds,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.designdbIds = []
  state.isPending = false
}

export default state
