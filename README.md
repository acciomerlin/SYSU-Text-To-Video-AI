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

将.env里的文件换成您自己的 api，我们文本生成用的是 deepseek，图片生产用的是通义万象，视频和音频生成用的是vidu，第一个充了 10 块可以用很久，第二个三个模型免费 500 张生成，第三个最少充 350 也还没用完，目前来讲是最省的开发环境了，想变可以自己 diy

启动前端应用：

```bash
streamlit run streamlit_app.py
```

##  3. 功能说明

启动应用后，界面如下：
<img width="1280" height="651" alt="image" src="https://github.com/user-attachments/assets/7700774d-864d-4ceb-bdbd-f0dbdd1720bb" />

支持以下功能：

- **剧本生成**：输入主题或关键词，自动生成五句故事剧本（中英文可选）
<img width="1280" height="538" alt="image" src="https://github.com/user-attachments/assets/967e60c4-7eb4-45bd-80ea-9764e29598ed" />
<img width="1280" height="658" alt="image" src="https://github.com/user-attachments/assets/7864283b-fbc7-43ca-a540-cba1f2d0d4a0" />

-  **剧本场景图生成**：选择图片风格（如像素、卡通），为每句话生成配图
<img width="1213" height="720" alt="image" src="https://github.com/user-attachments/assets/2c4aca5f-79b4-46a3-8b35-a654c3016a02" />
  - 示例输出：
<img width="1724" height="1032" alt="image" src="https://github.com/user-attachments/assets/240fdfac-5c78-4421-b86f-d67cf9930ca5" />

-  **图生视频 + 音频生成**：点击一键生成配图动画和对应旁白音频
<img width="1588" height="1076" alt="image" src="https://github.com/user-attachments/assets/cdc12269-161e-4bb2-b219-474b673f80a8" />

-  **视频合成**：三段及以上即可合成完整视频，加入字幕与音轨
<img width="1280" height="326" alt="image" src="https://github.com/user-attachments/assets/0de8e218-fff8-4a79-b60b-f9b762e43556" />
  - 示例输出：


https://github.com/user-attachments/assets/9ebe1816-e9c4-45d8-9d77-e7716d8be964


-  **历史记录**：每次生成的图像和视频自动保存在侧边栏，支持下载
<img width="486" height="1280" alt="image" src="https://github.com/user-attachments/assets/1db124e8-ad91-4eaa-83cc-073ef683fd4e" />

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

