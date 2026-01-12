# ComfyUI 集成指南

本项目已成功集成 ComfyUI 图片生成功能，支持通过工作流生成高质量图片。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install websocket-client
```

### 2. 启动 ComfyUI

确保你的 ComfyUI 服务正在运行：
```bash
# 默认地址为 127.0.0.1:8188
python main.py --listen 0.0.0.0 --port 8188
```

### 3. 配置项目

复制 `image_providers.yaml.example` 为 `image_providers.yaml` 并配置：

```yaml
active_provider: comfyui

providers:
  comfyui:
    type: comfyui
    server_address: "127.0.0.1:8188"
    workflow_file: "workflow_api.json"
    text_node_id: "57:45"
    seed_node_id: "57:44"
    width_node_id: "57:41"
    height_node_id: "57:41"
    default_width: 768
    default_height: 1024
    timeout: 300
    prompt_adapter:
      mode: "simple"  # simple | template | direct
      template_file: "comfyui_prompt.txt"
      max_length: 500
      preserve_keywords: ["高质量", "详细", "8k"]
    high_concurrency: false
```

## 📋 配置说明

### 基础配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `server_address` | ComfyUI 服务器地址 | `127.0.0.1:8188` |
| `workflow_file` | 工作流JSON文件路径 | `workflow_api.json` |
| `text_node_id` | 提示词节点ID | `57:45` |
| `seed_node_id` | 随机种子节点ID | `57:44` |
| `width_node_id` | 宽度节点ID | `57:41` |
| `height_node_id` | 高度节点ID | `57:41` |
| `timeout` | 超时时间（秒） | `300` |

### 提示词适配

ComfyUI 的提示词通常比大模型API更简洁，支持三种适配模式：

#### 1. Simple 模式（推荐）
```yaml
prompt_adapter:
  mode: "simple"
  max_length: 500
  preserve_keywords: ["高质量", "详细", "8k"]
```
- 提取核心内容，保留关键词
- 自动长度限制
- 适合大多数场景

#### 2. Template 模式
```yaml
prompt_adapter:
  mode: "template"
  template_file: "comfyui_prompt.txt"
```
- 使用自定义模板文件
- 完全控制提示词格式
- 适合高级用户

#### 3. Direct 模式
```yaml
prompt_adapter:
  mode: "direct"
```
- 直接使用原始提示词
- 不做任何处理
- 可能导致提示词过长

## 🧪 测试功能

运行测试脚本验证集成：

```bash
python test_comfyui.py
```

测试包括：
- 提示词适配功能
- 工作流加载
- 图片生成
- 错误处理

## 🎯 工作流配置

### 获取节点ID

1. 在 ComfyUI 中打开你的工作流
2. 点击 "Save (API Format)" 导出JSON
3. 找到关键节点的ID：
   - **文本节点**：通常是 `CLIPTextEncode` 类型
   - **种子节点**：通常是 `KSampler` 类型
   - **尺寸节点**：通常是 `EmptySD3LatentImage` 类型

### 推荐工作流结构

```
文本输入 → CLIP编码 → K采样器 → VAE解码 → 保存图片
    ↑
随机种子
    ↑
图片尺寸
```

## 🔧 高级功能

### 参考图片支持（计划中）

未来版本将支持：
- Image-to-Image
- ControlNet
- 风格迁移

### 多节点工作流

支持复杂的工作流，包括：
- 多个文本输入
- 条件控制
- 后处理节点

## 🐛 故障排除

### 常见问题

1. **连接失败**
   ```
   无法连接到ComfyUI WebSocket
   ```
   - 检查 ComfyUI 是否运行
   - 确认端口和地址正确
   - 检查防火墙设置

2. **工作流文件未找到**
   ```
   找不到工作流文件: workflow_api.json
   ```
   - 确认文件路径正确
   - 支持相对路径和绝对路径
   - 文件必须位于项目根目录或 `comfyUI/` 目录

3. **节点ID错误**
   ```
   找不到节点: 57:45
   ```
   - 重新导出工作流API格式
   - 检查节点ID是否正确
   - 确认节点类型匹配

4. **websocket-client 未安装**
   ```
   ImportError: No module named 'websocket'
   ```
   ```bash
   pip install websocket-client
   ```

### 调试模式

启用详细日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 开发说明

### 代码结构

```
backend/generators/
├── base.py              # 抽象基类
├── factory.py           # 工厂模式
├── comfyui.py          # ComfyUI生成器
└── ...

backend/prompts/
└── comfyui_prompt.txt   # ComfyUI专用模板
```

### 扩展功能

1. **自定义节点支持**
   ```python
   def _update_custom_node(self, workflow, value):
       self._update_node_value(workflow, "custom_node_id", "input_name", value)
   ```

2. **批量生成**
   ```python
   # 在 ImageService 中已支持并发
   high_concurrency: true
   ```

3. **自定义适配器**
   ```python
   class CustomPromptAdapter:
       def adapt(self, prompt, **kwargs):
           # 自定义适配逻辑
           return adapted_prompt
   ```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进 ComfyUI 集成功能！

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/henry4286/RedInk.git
cd RedInk

# 安装依赖
pip install -r requirements.txt
pip install websocket-client

# 启动开发服务器
python backend/app.py
```

## 📄 许可证

本项目遵循 MIT 许可证。

---

**注意**: ComfyUI 集成功能需要 ComfyUI 服务单独运行，请确保你有足够的硬件资源（推荐 GPU 8GB+）。