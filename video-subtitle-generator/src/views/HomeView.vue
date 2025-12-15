<template>
  <div class="home">
    <a-row :gutter="24">
      <a-col :span="12">
        <VideoUpload />
      </a-col>
      <a-col :span="12">
        <ProcessingStatus />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import VideoUpload from '@/components/VideoUpload.vue'
import ProcessingStatus from '@/components/ProcessingStatus.vue'
</script>

<style scoped>
.home {
  padding: 24px;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

:deep(.ant-row) {
  height: 100%;
}

:deep(.ant-col) {
  display: flex;
  align-items: stretch;
}
</style>