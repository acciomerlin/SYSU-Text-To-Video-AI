# SYSU-Text-To-Video-AI

一个基于大语言模型与多模态智能代理（Agent）的 AI 视频生成平台。
 用户只需输入一个校园主题创意，即可一键生成包含剧本、画面、音频、视频并自动合成的完整短视频。

## 1. 项目背景

AI 作画、AI 视频生成技术日益普及，但大众用户仍缺乏“**一句话生成创意视频**”的简单工具。

本项目聚焦校园主题，开发一个支持**文本 → 图像 → 视频 → 音频 → 合成短片**的智能生成工具，帮助用户快速将创意转化为具象的视频内容。

## 2. 安装与运行（Setup）

建议使用 Conda 创建隔离环境并安装依赖：

```bash
# 创建并激活名为 text2video 的新环境（Python 版本可根据需求调整）
conda create -n text2video python=3.10 -y
conda activate text2video

# 安装依赖
pip install -r requirements.txt
```

启动前端应用：

```bash
streamlit run streamlit_app.py
```

##  3. 功能说明

启动应用后，支持以下功能：

- **剧本生成**：输入主题或关键词，自动生成五句故事剧本（中英文可选）
-  **剧本场景图生成**：选择图片风格（如像素、卡通），为每句话生成配图
-  **图生视频 + 音频生成**：点击一键生成配图动画和对应旁白音频
-  **视频合成**：三段及以上即可合成完整视频，加入字幕与音轨
-  **历史记录**：每次生成的图像和视频自动保存在侧边栏，支持下载

## 4. 项目目录结构说明

```bash
.
├── streamlit_app.py              # 主入口，Streamlit 前端与生成图、音视频、合成视频逻辑
├── requirements.txt              # 依赖包
├── .env                          # API 密钥等环境配置（本地配置）
├── testUtility/                  # 测试各模块功能的demo
│   ├── findfont.py
│   ├── test_all.py
│   ├── test_ui.py
│   └── video.py
├── utility/                      # 我们将历史记录与剧本生成两个比较大的功能独立出来
│   ├── history/                  # 历史记录模块
│   │   └── history_manager.py
│   └── script/                   # 剧本生成模块
│       └── script_generator.py
```

