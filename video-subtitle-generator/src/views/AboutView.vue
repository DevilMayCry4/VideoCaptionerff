<template>
  <div class="about">
    <a-card title="关于视频字幕生成器" class="about-card">
      <div class="about-content">
        <h2>🎬 视频字幕生成器</h2>
        <p class="description">
          这是一个基于人工智能的自动字幕生成工具，能够将视频中的语音内容自动转换为文字字幕。
        </p>
        
        <div class="features">
          <h3>✨ 主要功能</h3>
          <ul>
            <li>支持多种视频格式：MP4、MOV、AVI、WMV</li>
            <li>自动音频提取和字幕生成</li>
            <li>实时进度显示和状态监控</li>
            <li>支持字幕预览和下载</li>
            <li>批量处理和任务管理</li>
          </ul>
        </div>

        <div class="tech-stack">
          <h3>🛠️ 技术栈</h3>
          <a-row :gutter="16">
            <a-col :span="8">
              <a-card size="small" title="前端">
                <ul>
                  <li>Vue 3 + TypeScript</li>
                  <li>Ant Design Vue</li>
                  <li>Vite</li>
                  <li>Pinia</li>
                </ul>
              </a-card>
            </a-col>
            <a-col :span="8">
              <a-card size="small" title="后端">
                <ul>
                  <li>Flask</li>
                  <li>Python 3.9</li>
                  <li>faster-whisper</li>
                  <li>ffmpeg</li>
                </ul>
              </a-card>
            </a-col>
            <a-col :span="8">
              <a-card size="small" title="AI模型">
                <ul>
                  <li>OpenAI Whisper</li>
                  <li>多语言支持</li>
                  <li>高精度识别</li>
                  <li>GPU加速</li>
                </ul>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <div class="usage">
          <h3>📖 使用说明</h3>
          <ol>
            <li>上传视频文件（支持拖拽上传）</li>
            <li>等待系统自动处理（音频提取 → 字幕生成）</li>
            <li>查看处理进度和结果</li>
            <li>下载生成的字幕文件</li>
          </ol>
        </div>

        <div class="performance">
          <h3>⚡ 性能特点</h3>
          <ul>
            <li>10分钟视频处理时间约3分钟（GPU环境）</li>
            <li>支持并发处理多个任务</li>
            <li>智能缓存机制，避免重复处理</li>
            <li>断点续传和错误重试</li>
          </ul>
        </div>

        <div class="footer">
          <a-divider />
          <p class="version">版本：v1.0.0</p>
          <p class="author">开发者：AI助手</p>
          <p class="license">开源协议：MIT License</p>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
// 关于页面组件
</script>

<style scoped>
.about {
  padding: 24px;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.about-card {
  max-width: 1200px;
  margin: 0 auto;
}

.about-content {
  padding: 24px;
}

.about-content h2 {
  text-align: center;
  color: #1890ff;
  margin-bottom: 24px;
  font-size: 32px;
  font-weight: 600;
}

.about-content h3 {
  color: #262626;
  margin: 24px 0 16px 0;
  font-size: 20px;
  font-weight: 500;
}

.description {
  text-align: center;
  font-size: 16px;
  color: #666;
  margin-bottom: 32px;
  line-height: 1.6;
}

.features ul,
.usage ol,
.performance ul {
  background: #f5f5f5;
  padding: 16px 24px;
  border-radius: 6px;
  border-left: 4px solid #1890ff;
}

.features li,
.usage li,
.performance li {
  margin: 8px 0;
  color: #262626;
  font-size: 14px;
  line-height: 1.5;
}

.tech-stack {
  margin: 24px 0;
}

.tech-stack ul {
  margin: 0;
  padding-left: 20px;
}

.tech-stack li {
  margin: 4px 0;
  color: #262626;
  font-size: 13px;
}

.footer {
  text-align: center;
  margin-top: 32px;
}

.footer p {
  margin: 8px 0;
  color: #666;
  font-size: 14px;
}

:deep(.ant-card-head-title) {
  font-size: 20px;
  font-weight: 600;
  color: #262626;
}

:deep(.ant-card-body) {
  padding: 0;
}
</style>