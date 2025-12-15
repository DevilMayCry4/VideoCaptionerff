import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface VideoTask {
  id: string
  originalFilename: string
  status: 'pending' | 'processing' | 'extracting' | 'transcribing' | 'completed' | 'failed'
  progress: number
  message: string
  error?: string
  subtitleContent?: string
  subtitlePath?: string
}

export const useVideoStore = defineStore('video', () => {
  const tasks = ref<VideoTask[]>([])
  const currentTask = ref<VideoTask | null>(null)

  const addTask = (file: File) => {
    const task: VideoTask = {
      id: Date.now().toString(),
      originalFilename: file.name,
      status: 'pending',
      progress: 0,
      message: '等待处理...'
    }
    tasks.value.push(task)
    currentTask.value = task
    return task.id
  }

  const updateTask = (taskId: string, updates: Partial<VideoTask>) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      Object.assign(task, updates)
      if (currentTask.value?.id === taskId) {
        currentTask.value = task
      }
    }
  }

  const removeTask = (taskId: string) => {
    const index = tasks.value.findIndex(t => t.id === taskId)
    if (index > -1) {
      tasks.value.splice(index, 1)
      if (currentTask.value?.id === taskId) {
        currentTask.value = null
      }
    }
  }

  const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed'))
  const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'pending' || t.status === 'processing'))

  return {
    tasks,
    currentTask,
    addTask,
    updateTask,
    removeTask,
    completedTasks,
    pendingTasks
  }
})