<template>
  <div class="video-upload">
    <a-upload-dragger
      v-model:fileList="fileList"
      :before-upload="beforeUpload"
      :accept="acceptedFormats"
      :multiple="true"
      @change="handleChange"
      @drop="handleDrop"
      class="upload-area"
    >
      <p class="ant-upload-drag-icon">
        <inbox-outlined />
      </p>
      <p class="ant-upload-text">点击或拖拽视频文件到此处上传</p>
      <p class="ant-upload-hint">
        支持 {{ acceptedFormats }} 格式，文件大小不超过 500MB
      </p>
    </a-upload-dragger>

    <div class="folder-select" style="margin-top:16px;">
      <button class="ant-btn" @click.prevent="triggerFolderSelect">选择文件夹</button>
      <input ref="folderInput" type="file" webkitdirectory directory multiple style="display:none" @change="handleFolderSelect" />
      <button v-if="selectedFiles.length" class="ant-btn ant-btn-primary" style="margin-left:8px;" @click="uploadAllFromFolder">上传全部</button>
    </div>

    <div v-if="selectedFiles.length" class="selected-list" style="margin-top:12px;">
      <strong>已选文件：</strong>
      <ul>
        <li v-for="(f, idx) in selectedFiles" :key="idx">{{ f.name }} ({{ (f.size/1024/1024).toFixed(2) }} MB)</li>
      </ul>
    </div>

    <div v-if="uploading" class="upload-progress">
      <a-progress 
        :percent="uploadPercent" 
        :status="uploadStatus"
        :stroke-color="{
          '0%': '#108ee9',
          '100%': '#87d068',
        }"
      />
      <p class="upload-status">{{ uploadMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useVideoStore } from '@/stores/videoStore'

const videoStore = useVideoStore()

const fileList = ref([])
const uploading = ref(false)
const uploadPercent = ref(0)
const uploadStatus = ref<'active' | 'success' | 'exception'>('active')
const uploadMessage = ref('')

// 目录选择与批量上传相关
const selectedFiles = ref<File[]>([])
const folderInput = ref<HTMLInputElement | null>(null)

const triggerFolderSelect = () => {
  folderInput.value?.click()
}

const handleFolderSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const files = Array.from(input.files)

  // 过滤符合的视频文件
  const allowedExtensions = ['.mp4', '.mov', '.avi', '.wmv']
  const valid = files.filter(f => {
    const ext = f.name.toLowerCase().substring(f.name.lastIndexOf('.'))
    return allowedExtensions.includes(ext) && f.size <= maxFileSize
  })

  if (!valid.length) {
    message.warn('未发现符合条件的视频文件（或文件过大）。')
    return
  }

  selectedFiles.value = valid
  message.success(`已选中 ${valid.length} 个视频文件`) 
}

const uploadAllFromFolder = async () => {
  if (!selectedFiles.value.length) return
  uploading.value = true
  for (const file of selectedFiles.value) {
    const ok = beforeUpload(file)
    if (!ok) {
      videoStore.updateTask(videoStore.addTask(file), { status: 'failed', message: '文件验证失败' })
      continue
    }

    const taskId = videoStore.addTask(file)
    uploadMessage.value = `正在上传 ${file.name}`
    uploadPercent.value = 0
    try {
      await startProcessing(taskId, file)
    } catch (err) {
      console.error('单文件处理失败', err)
    }
  }
  uploading.value = false
  selectedFiles.value = []
  message.success('文件夹中的视频处理完成')
}

const acceptedFormats = '.mp4,.mov,.avi,.wmv'
const maxFileSize = 500 * 1024 * 1024 // 500MB

const beforeUpload = (file: File) => {
  // 验证文件格式
  const allowedTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-ms-wmv']
  const allowedExtensions = ['.mp4', '.mov', '.avi', '.wmv']
  
  const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
  
  if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
    message.error('不支持的文件格式，请选择 MP4、MOV、AVI 或 WMV 格式的视频文件')
    return false
  }
  
  // 验证文件大小
  if (file.size > maxFileSize) {
    message.error('文件大小超过 500MB 限制')
    return false
  }
  
  return true
}

const handleChange = (info: any) => {
  const status = info.file.status
  
  if (status === 'uploading') {
    uploading.value = true
    uploadPercent.value = info.file.percent || 0
    uploadStatus.value = 'active'
    uploadMessage.value = '正在上传...'
  } else if (status === 'done') {
    uploadPercent.value = 100
    uploadStatus.value = 'success'
    uploadMessage.value = '上传成功，开始处理...'
    
    // 添加到任务队列
    const taskId = videoStore.addTask(info.file.originFileObj)
    
    // 模拟上传完成后的处理
    setTimeout(() => {
      startProcessing(taskId, info.file.originFileObj)
    }, 1000)
    
  } else if (status === 'error') {
    uploading.value = false
    uploadStatus.value = 'exception'
    uploadMessage.value = '上传失败'
    message.error('文件上传失败')
  }
}

const handleDrop = (e: DragEvent) => {
  console.log('Drop event:', e)
}

const startProcessing = async (taskId: string, file: File) => {
  try {
    // 创建 FormData
    const formData = new FormData()
    formData.append('file', file)
    
    // 模拟上传进度
    uploadMessage.value = '正在发送到服务器...'
    
    // 这里应该调用实际的上传API
    // const response = await fetch('/api/upload', {
    //   method: 'POST',
    //   body: formData
    // })
    
    // 模拟处理进度
    await simulateProcessing(taskId)
    
  } catch (error) {
    console.error('处理失败:', error)
    videoStore.updateTask(taskId, {
      status: 'failed',
      message: '处理失败',
      error: error instanceof Error ? error.message : '未知错误'
    })
    uploadStatus.value = 'exception'
    uploadMessage.value = '处理失败'
  } finally {
    uploading.value = false
  }
}

const simulateProcessing = async (taskId: string) => {
  // 模拟处理过程
  const steps = [
    { status: 'processing' as const, progress: 20, message: '正在初始化...', delay: 1000 },
    { status: 'extracting' as const, progress: 40, message: '正在提取音频...', delay: 3000 },
    { status: 'transcribing' as const, progress: 60, message: '正在生成字幕...', delay: 5000 },
    { status: 'completed' as const, progress: 100, message: '处理完成！', delay: 1000 }
  ]
  
  for (const step of steps) {
    await new Promise(resolve => setTimeout(resolve, step.delay))
    videoStore.updateTask(taskId, {
      status: step.status,
      progress: step.progress,
      message: step.message
    })
    uploadPercent.value = step.progress
    uploadMessage.value = step.message
  }
  
  // 模拟字幕内容
  videoStore.updateTask(taskId, {
    subtitleContent: `1
00:00:00,000 --> 00:00:03,000
欢迎使用视频字幕生成器

2
00:00:03,000 --> 00:00:06,000
这是模拟生成的字幕内容`,
    subtitlePath: `/subtitles/${taskId}.srt`
  })
}
</script>

<style scoped>
.video-upload {
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.upload-area {
  margin-bottom: 24px;
}

.upload-progress {
  margin-top: 24px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 6px;
}

.upload-status {
  margin-top: 12px;
  color: #666;
  font-size: 14px;
  text-align: center;
}

:deep(.ant-upload-drag-icon) {
  margin-bottom: 16px;
}

:deep(.ant-upload-drag-icon .anticon) {
  font-size: 48px;
  color: #1890ff;
}

:deep(.ant-upload-text) {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

:deep(.ant-upload-hint) {
  color: #999;
  font-size: 14px;
}
</style>