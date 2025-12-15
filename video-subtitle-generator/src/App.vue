<template>
  <a-config-provider :locale="zhCN">
    <a-layout class="layout">
      <a-layout-header class="header">
        <div class="logo">
          <h1>🎬 视频字幕生成器</h1>
        </div>
        <a-menu
          theme="dark"
          mode="horizontal"
          :selected-keys="[$route.path]"
          :style="{ lineHeight: '64px' }"
        >
          <a-menu-item key="/">
            <router-link to="/">首页</router-link>
          </a-menu-item>
          <a-menu-item key="/about">
            <router-link to="/about">关于</router-link>
          </a-menu-item>
        </a-menu>
      </a-layout-header>
      
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
      
      <a-layout-footer class="footer">
        <div class="footer-content">
          <p>&copy; 2024 视频字幕生成器. 基于 Vue + Flask + faster-whisper 技术栈</p>
          <p>支持 MP4、MOV、AVI、WMV 格式视频文件</p>
        </div>
      </a-layout-footer>
    </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import zhCN from 'ant-design-vue/es/locale/zh_CN'
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.header {
  background: #001529;
  padding: 0 50px;
  display: flex;
  align-items: center;
}

.logo {
  color: white;
  margin-right: 40px;
}

.logo h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.content {
  padding: 0;
  background: #f0f2f5;
}

.footer {
  background: #001529;
  color: white;
  text-align: center;
  padding: 24px 50px;
}

.footer-content p {
  margin: 8px 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 14px;
}

:deep(.ant-layout-header) {
  display: flex;
  align-items: center;
}

:deep(.ant-menu-dark) {
  background: transparent;
}
</style>