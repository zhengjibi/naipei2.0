# Naipei 2.0 — 桌面宠物

一只基于 Python 的互动桌面宠物，漂浮在桌面上与你互动。点击、拖拽、语音对话、红温暴怒，应有尽有。

## 2.0 更新内容

### 新增功能
- **语音气泡** — 所有语音对话同步显示文字气泡，悬浮在精灵头顶
- **右键双击退出** — 快速双击右键，精灵说"拜拜"后退出
- **边缘反弹** — 走动碰到屏幕边缘自动调头，不再卡墙
- **全屏随机走动** — 闲置时在屏幕任意位置走动，不再只水平移动
- **红温灵敏度提升** — 3 秒内点击 5 次即可触发（原 8 次）
- **左键语音反馈** — 点击时精灵会说"主人不要啊"
- **中键狗叫** — 按滚轮键播放狗叫声

### 交互优化
- 拖拽防抖阈值提升至 8px，快速点击不再误触拖拽
- 松手掉落物理重写，画面感更强
- 气泡使用独立窗口，不干扰精灵点击区域
- 气泡显示时长按字数自动适配
- TTS 每次新建引擎，避免语音冲突

## 完整功能

| 操作 | 效果 |
|------|------|
| 左键单击 | 弹跳 + "主人不要啊" |
| 左键拖拽 | 移动精灵（松手掉落回屏幕底部） |
| 左键双击 | 开心蹦跳 |
| 滚轮键（中键） | 狗叫 |
| 鼠标滚轮 | 缩放大小 |
| 右键单击 | 语音对话（录音 → 识别 → DeepSeek → 朗读 + 气泡） |
| 右键双击 | 退出 |
| 快速连点 ≥5 次/3 秒 | 红温暴怒（变红 + "别再搞我了！"） |
| 拖到屏幕顶部 | 退出 |

### 自动行为
- 2~5 秒间隔随机跳跃或全屏走动
- 碰到屏幕边缘反弹

## 安装与运行

### 依赖
```bash
pip install pillow pyttsx3 SpeechRecognition pyaudio pygame requests
```

### 运行
```bash
python desktop_pet.pyw
```

### 配置 DeepSeek API Key（语音对话必需）
设置环境变量：
```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-你的key", "User")
```

## 文件结构
```
naipei2.0/
  desktop_pet.pyw    # 主程序
  assets/
    pet.png          # 精灵形象（192x208）
    dog.mp3          # 狗叫声
  README.md
```

## 自定义
- 替换 `assets/pet.png` 为你的角色图片（192x208，透明背景）
- 替换 `assets/dog.mp3` 为喜欢的声音

## 技术栈
Python 3.10+ · tkinter · PIL/Pillow · pygame · pyttsx3 · SpeechRecognition · DeepSeek API

## License
MIT
