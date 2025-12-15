<template>
  <div class="processing-status">
    <a-card title="处理状态" class="status-card">
      <div v-if="currentTask" class="current-task">
        <div class="task-info">
          <h3>{{ currentTask.originalFilename }}</h3>
          <a-tag :color="getStatusColor(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </a-tag>
        </div>
        
        <div class="progress-section">
          <a-progress 
            :percent="currentTask.progress" 
            :status="getProgressStatus(currentTask.status)"
            :stroke-color="getProgressColor(currentTask.status)"
            size="large"
          />
          <p class="progress-message">{{ currentTask.message }}</p>
        </div>

        <div v-if="currentTask.error" class="error-section">
          <a-alert
            :message="currentTask.error"
            type="error"
            show-icon
            closable
          />
        </div>

        <div v-if="currentTask.status === 'completed' && currentTask.subtitleContent" class="result-section">
          <a-divider />
          <h4>字幕预览</h4>
          <div class="subtitle-preview">
            <pre>{{ currentTask.subtitleContent }}</pre>
          </div>
          <div class="action-buttons">
            <a-button type="primary" @click="downloadSubtitle" icon="download">
              下载字幕文件
            </a-button>
            <a-button @click="copySubtitle" icon="copy">
              复制字幕内容
            </a-button>
          </div>
        </div>
      </div>
      
      <div v-else class="no-task">
        <a-empty description="暂无处理任务" />
      </div>
    </a-card>

    <!-- 历史任务列表 -->
    <a-card title="历史任务" class="history-card" v-if="completedTasks.length > 0">
      <a-list :data-source="completedTasks" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta
              :title="item.originalFilename"
              :description="`完成时间: ${new Date(parseInt(item.id)).toLocaleString()}`"
            >
              <template #avatar>
                <a-icon type="check-circle" theme="twoTone" two-tone-color="#52c41a" />
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button size="small" @click="viewTask(item)">查看</a-button>
              <a-button size="small" @click="downloadTaskSubtitle(item)">下载</a-button>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { message } from 'ant-design-vue'
import { useVideoStore, type VideoTask } from '@/stores/videoStore'

const videoStore = useVideoStore()

const currentTask = computed(() => videoStore.currentTask)
const completedTasks = computed(() => videoStore.completedTasks)

const getStatusColor = (status: string) => {
  const colorMap = {
    pending: 'default',
    processing: 'processing',
    extracting: 'processing',
    transcribing: 'processing',
    completed: 'success',
    failed: 'error'
  }
  return colorMap[status as keyof typeof colorMap] || 'default'
}

const getStatusText = (status: string) => {
  const textMap = {
    pending: '等待处理',
    processing: '处理中',
    extracting: '提取音频',
    transcribing: '生成字幕',
    completed: '完成',
    failed: '失败'
  }
  return textMap[status as keyof typeof textMap] || status
}

const getProgressStatus = (status: string) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  return 'active'
}

const getProgressColor = (status: string) => {
  if (status === 'failed') return '#ff4d4f'
  if (status === 'completed') return '#52c41a'
  return {
    '0%': '#108ee9',
    '100%': '#87d068'
  }
}

const downloadSubtitle = () => {
  if (!currentTask.value?.subtitleContent) return
  
  const blob = new Blob([currentTask.value.subtitleContent], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${currentTask.value.originalFilename.replace(/\.[^/.]+$/, '')}.srt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  message.success('字幕文件下载成功')
}

const copySubtitle = () => {
  if (!currentTask.value?.subtitleContent) return
  
  navigator.clipboard.writeText(currentTask.value.subtitleContent).then(() => {
    message.success('字幕内容已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败，请手动复制')
  })
}

const viewTask = (task: VideoTask) => {
  videoStore.currentTask = task
}

const downloadTaskSubtitle = (task: VideoTask) => {
  if (!task.subtitleContent) return
  
  const blob = new Blob([task.subtitleContent], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${task.originalFilename.replace(/\.[^/.]+$/, '')}.srt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  message.success('字幕文件下载成功')
}
</script>

<style scoped>
.processing-status {
  padding: 24px;
}

.status-card {
  margin-bottom: 24px;
}

.current-task {
  padding: 16px 0;
}

.task-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.task-info h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}

.progress-section {
  margin-bottom: 24px;
}

.progress-message {
  margin-top: 12px;
  color: #666;
  font-size: 14px;
  text-align: center;
}

.error-section {
  margin-bottom: 24px;
}

.result-section {
  margin-top: 24px;
}

.subtitle-preview {
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 16px;
  margin: 16px 0;
  max-height: 300px;
  overflow-y: auto;
}

.subtitle-preview pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #262626;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 16px;
}

.no-task {
  text-align: center;
  padding: 48px 0;
}

.history-card {
  margin-top: 24px;
}

:deep(.ant-list-item-action) {
  display: flex;
  gap: 8px;
}

:deep(.ant-list-item-action .ant-btn) {
  padding: 0 8px;
  height: 24px;
  font-size: 12px;
}
</style>