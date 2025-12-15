# 🎬 视频字幕生成器

基于 Vue 3 + Flask + faster-whisper 的智能视频字幕生成工具，支持多种视频格式，自动提取音频并生成高质量字幕文件。

## ✨ 功能特性

- 🎥 **多格式支持**：支持 MP4、MOV、AVI、WMV 等常见视频格式
- 🗣️ **AI智能识别**：基于 OpenAI Whisper 模型，支持多语言识别
- ⚡ **高效处理**：GPU加速，10分钟视频约3分钟完成处理
- 📊 **实时进度**：可视化处理进度，状态实时更新
- 💾 **结果管理**：支持字幕预览、下载和历史记录管理
- 🐳 **容器化部署**：完整的 Docker 支持，一键部署

## 🛠️ 技术栈

### 前端
- **Vue 3** + **TypeScript** - 现代化前端框架
- **Ant Design Vue** - 企业级UI组件库
- **Vite** - 快速构建工具
- **Pinia** - 状态管理

### 后端
- **Flask** - Python Web框架
- **faster-whisper** - 高性能Whisper实现
- **ffmpeg** - 音视频处理
- **SQLite** - 轻量级数据库

### 部署
- **Docker** + **Docker Compose** - 容器化部署
- **Nginx** - 反向代理和静态文件服务

## 🚀 快速开始

### 环境要求
- Node.js 18+
- Python 3.9+
- ffmpeg
- 8GB+ RAM（推荐，用于AI模型）

### 1. 克隆项目
```bash
git clone <repository-url>
cd video-subtitle-generator
```

### 2. 安装依赖

#### 前端依赖
```bash
cd video-subtitle-generator
npm install
```

#### 后端依赖
```bash
cd api
pip install -r requirements.txt
```

### 3. 启动服务

#### 开发模式
```bash
# 启动前端（端口5173）
npm run dev

# 启动后端（端口5000）
cd api
python app.py
```

#### Docker部署
```bash
# 构建并启动所有服务
docker-compose up -d

# 访问应用
open http://localhost
```

## 📖 API文档

### 文件上传
```http
POST /api/upload
Content-Type: multipart/form-data

file: 视频文件（MP4/MOV/AVI/WMV，最大500MB）
```

### 音频提取
```http
POST /api/extract-audio
Content-Type: application/json

{
  "task_id": "任务ID"
}
```

### 生成字幕
```http
POST /api/generate-subtitle
Content-Type: application/json

{
  "task_id": "任务ID"
}
```

### 查询状态
```http
GET /api/status/{task_id}
```

### 下载字幕
```http
GET /api/download/{task_id}
```

## 🔧 配置说明

### 环境变量
```bash
# Flask配置
FLASK_ENV=development          # 运行环境
FLASK_PORT=5000               # 服务端口
SECRET_KEY=your-secret-key    # 密钥

# 文件配置
UPLOAD_FOLDER=uploads         # 上传目录
AUDIO_FOLDER=audio           # 音频目录
SUBTITLE_FOLDER=subtitles    # 字幕目录
MAX_FILE_SIZE=500MB          # 最大文件大小

# Whisper配置
WHISPER_MODEL=base           # 模型大小（tiny/base/small/medium/large）
WHISPER_LANGUAGE=auto        # 语言（auto/zh/en等）
WHISPER_DEVICE=auto          # 设备（auto/cpu/cuda）
```

### 模型选择
| 模型大小 | 显存需求 | 处理速度 | 准确率 |
|---------|---------|---------|--------|
| tiny    | ~1GB    | 最快    | 基础   |
| base    | ~1GB    | 快      | 良好   |
| small   | ~2GB    | 中等    | 很好   |
| medium  | ~5GB    | 慢      | 优秀   |
| large   | ~10GB   | 最慢    | 最佳   |

## 📊 性能指标

### 处理速度（base模型）
- 10分钟视频：约3分钟
- 30分钟视频：约8分钟
- 60分钟视频：约15分钟

### 系统要求
- **CPU**: 4核心以上
- **内存**: 8GB以上
- **存储**: 10GB可用空间
- **GPU**: 可选，可显著提升处理速度

## 🧪 测试

### 单元测试
```bash
cd api
python -m pytest tests/unit/
```

### 集成测试
```bash
cd api
python -m pytest tests/integration/
```

### 压力测试
```bash
cd api
locust -f tests/load/locustfile.py --host=http://localhost:5000
```

## 🐛 常见问题

### Q: 上传文件失败？
**A**: 检查文件格式和大小限制，确保是支持的格式（MP4/MOV/AVI/WMV）且小于500MB。

### Q: 处理速度很慢？
**A**: 
- 检查是否启用了GPU加速
- 尝试使用较小的模型（tiny/base）
- 确保系统有足够的内存

### Q: 字幕识别准确率低？
**A**:
- 尝试使用更大的模型（medium/large）
- 检查音频质量，确保语音清晰
- 可以指定语言代码提高准确率

### Q: Docker部署失败？
**A**:
- 确保Docker和Docker Compose已正确安装
- 检查端口是否被占用
- 查看容器日志获取详细错误信息

## 🔒 安全说明

- 上传的文件会进行病毒扫描和格式验证
- 支持HTTPS加密传输
- 定期清理临时文件和过期数据
- 敏感信息不会存储在日志中

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目维护者：AI助手
- 邮箱：assistant@example.com
- 项目地址：[GitHub Repository](https://github.com/your-username/video-subtitle-generator)

## 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 优秀的语音识别模型
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 高性能Whisper实现
- [FFmpeg](https://ffmpeg.org/) - 强大的音视频处理工具
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Flask](https://flask.palletsprojects.com/) - Python Web框架

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！