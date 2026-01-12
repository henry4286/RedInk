"""ComfyUI 图片生成器 - Refactored"""
import json
import os
import copy
import logging
import uuid
import time
import urllib.request
import urllib.parse
import random
from typing import Dict, Any, Optional, List, Callable, Tuple
from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)

import websocket


class ComfyUIGenerator(ImageGeneratorBase):
    """ComfyUI 生成器 (优化版)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.debug("初始化 ComfyUIGenerator...")
        
        # 1. 基础配置
        self.server_address = config.get('server_address', '127.0.0.1:8188')
        self.http_base = f"http://{self.server_address}"
        self.ws_base = f"ws://{self.server_address}/ws"
        self.client_id = str(uuid.uuid4())
        self.timeout = config.get('timeout', 300)
        
        # 2. 工作流节点配置
        self.workflow_file = config.get('workflow_file', 'workflow_api.json')
        self.text_node_id = config.get('text_node_id', '57:45')
        self.seed_node_id = config.get('seed_node_id', '57:44')
        self.width_node_id = config.get('width_node_id', '57:41')
        self.default_width = config.get('default_width', 768)
        self.default_height = config.get('default_height', 1024)
        
        # 3. 提示词适配配置
        self.prompt_mode = config.get('prompt_adapter_mode', 'simple')
        self.max_prompt_length = config.get('max_prompt_length', 2000)
        
        # 4. 加载资源
        self._init_paths()
        self.workflow_template = self._load_workflow_template()
        self.comfy_prompt_template = self._load_comfy_prompt_template() if self.prompt_mode == 'template' else None
        
        logger.info(f"ComfyUIGenerator 初始化完成: server={self.server_address}, mode={self.prompt_mode}")

    def _init_paths(self):
        """初始化相关路径"""
        # 假设当前文件在 backend/generators/comfyui.py
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # 工作流文件首选位置：项目根目录下的 comfyUI 文件夹
        self.workflow_dir = os.path.join(self.base_dir, 'comfyUI')
        # 提示词模板位置：backend/prompts/
        self.prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

    def validate_config(self) -> bool:
        """验证配置并测试连接"""
        if not self.server_address:
            raise ValueError("ComfyUI 服务器地址未配置")
        
        # 测试连接
        try:
            test_url = f"{self.http_base}/system_stats"
            with urllib.request.urlopen(test_url, timeout=5) as response:
                if response.status == 200:
                    logger.debug("ComfyUI 服务器连接正常")
                    return True
        except Exception as e:
            logger.warning(f"ComfyUI 服务器连接测试失败: {e}")
            # 这里选择不抛出异常，允许离线配置，但在生成时会失败
        return True

    # ===========================
    # 资源加载方法 (简化路径逻辑)
    # ===========================
    
    def _load_workflow_template(self) -> Dict[str, Any]:
        """加载工作流模板"""
        # 优先查找 comfyUI 子目录，其次查找根目录
        potential_paths = [
            os.path.join(self.workflow_dir, self.workflow_file),
            os.path.join(self.base_dir, self.workflow_file)
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                logger.info(f"加载工作流模板: {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        raise FileNotFoundError(f"找不到工作流文件: {self.workflow_file}，已搜索路径: {potential_paths}")

    def _load_comfy_prompt_template(self) -> Optional[str]:
        """加载专用提示词模板"""
        template_path = os.path.join(self.prompts_dir, 'comfyui_prompt.txt')
        
        if os.path.exists(template_path):
            logger.info(f"✅ 加载提示词模板: {template_path}")
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        logger.warning(f"❌ 找不到提示词模板: {template_path}，将回退到简单模式")
        return None

    # ===========================
    # 提示词处理方法 (核心优化区域)
    # ===========================

    def _get_page_type_guidance(self, page_type: str) -> str:
        """获取页面类型的指导要求"""
        guidance_map = {
            "cover": """- 标题占据主要位置，字号最大\n
                        - 副标题居中或在标题下方\n
                        - 整体设计要有吸引力和冲击力\n
                        - 背景可以更丰富，有视觉焦点""",
            "content": """- 信息层次分明\n
                        - 列表项清晰展示\n
                        - 重点内容用颜色或粗体强调\n
                        - 可以有小图标辅助说明""",
            "summary": """- 总结性文字突出\n
                        - 可以有勾选框或完成标志\n
                        - 给人完成感和满足感\n
                        - 鼓励性的视觉元素"""
        }
        return guidance_map.get(page_type, "")

    def _adapt_prompt(self, prompt: str, page_type: str = "", page_content: str = "") -> str:
        """
        适配提示词。
        优化点：将页面类型的指导信息融入到具体内容中，再嵌入大模板。
        """
        # 1. 确定核心内容来源
        core_content = page_content if page_content else prompt
        
        # 2. 获取页面类型特定的指导信息
        type_guidance = self._get_page_type_guidance(page_type)
        
        # 3. 组合特定内容（指导信息 + 核心描述）
        combined_specific_content = f"{type_guidance}\n{core_content}" if type_guidance else core_content

        # 4. 应用模板
        if self.prompt_mode == 'template' and self.comfy_prompt_template:
            # 使用大模板包裹组合后的内容
            adapted_prompt = self.comfy_prompt_template.format(
                outline_specific_content=core_content,
                type_specific_content=type_guidance
            )
        else:
            # 简单模式
            prefix = f"小红书风格{page_type}页面：" if page_type else "小红书风格："
            adapted_prompt = f"{prefix}{combined_specific_content}"
        
        # 5. 长度截断
        if len(adapted_prompt) > self.max_prompt_length:
            adapted_prompt = adapted_prompt[:self.max_prompt_length] + "..."
            logger.warning(f"提示词已截断至 {self.max_prompt_length} 字符")
        
        # 将详细提示词日志降级为 DEBUG，避免生产环境刷屏
        logger.debug(f"提示词适配结果 (长度 {len(adapted_prompt)}):\n{adapted_prompt}...")
        return adapted_prompt

    # ===========================
    # ComfyUI API 交互方法
    # ===========================

    def _update_node(self, workflow: Dict, node_id: str, input_key: str, value: Any):
        """安全的更新节点值"""
        if node_id and node_id in workflow and 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][input_key] = value
        else:
            logger.warning(f"无法更新节点 [{node_id}]:[{input_key}]，节点不存在或配置错误")

    def _queue_prompt(self, workflow: Dict) -> str:
        """发送排队请求"""
        data = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode('utf-8')
        req = urllib.request.Request(f"{self.http_base}/prompt", data=data, method="POST", headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())['prompt_id']

    def _connect_websocket(self) -> websocket.WebSocket:
        """建立 WebSocket 连接"""
        if websocket is None:
            raise ImportError("websocket-client 未安装")
        ws = websocket.WebSocket()
        ws.connect(f"{self.ws_base}?clientId={self.client_id}", timeout=10)
        return ws

    def _monitor_execution(self, ws: websocket.WebSocket, prompt_id: str, progress_callback: Optional[Callable] = None) -> float:
        """监听执行进度直到完成，返回耗时"""
        start_time = time.time()
        while True:
            try:
                out = ws.recv()
                if not isinstance(out, str): continue
                
                message = json.loads(out)
                if message.get('data', {}).get('prompt_id') != prompt_id:
                    continue
                    
                msg_type = message.get('type')
                data = message.get('data', {})

                if msg_type == 'progress':
                    value, max_val = data.get('value', 0), data.get('max', 1)
                    percent = int((value / max_val) * 100)
                    logger.debug(f"ComfyUI进度: {percent}%")
                    if progress_callback:
                        progress_callback({'type': 'progress', 'percent': percent, 'value': value, 'max_value': max_val})
                
                elif msg_type == 'execution_start':
                    node_type = data.get('node_type', 'Unknown')
                    logger.debug(f"开始执行节点: {node_type}")
                    if progress_callback:
                        progress_callback({'type': 'node_start', 'node_type': node_type})

                elif msg_type == 'executing' and data.get('node') is None:
                    # 任务完成
                    elapsed = time.time() - start_time
                    logger.info(f"任务 {prompt_id} 完成，耗时: {elapsed:.2f}s")
                    if progress_callback:
                        progress_callback({'type': 'complete', 'elapsed': elapsed})
                    return elapsed

            except websocket.WebSocketConnectionClosedException:
                raise Exception("WebSocket 连接意外断开")

    def _download_generated_images(self, prompt_id: str) -> List[bytes]:
        """下载指定任务生成的所有图片"""
        history = self._get_history(prompt_id)
        outputs = history.get(prompt_id, {}).get('outputs', {})
        
        image_data_list = []
        for node_output in outputs.values():
            for img_info in node_output.get('images', []):
                query = urllib.parse.urlencode({
                    "filename": img_info['filename'],
                    "subfolder": img_info['subfolder'],
                    "type": img_info['type']
                })
                with urllib.request.urlopen(f"{self.http_base}/view?{query}", timeout=self.timeout) as response:
                    image_data_list.append(response.read())
        
        logger.info(f"成功下载 {len(image_data_list)} 张图片")
        return image_data_list

    def _get_history(self, prompt_id: str) -> Dict:
        with urllib.request.urlopen(f"{self.http_base}/history/{prompt_id}", timeout=10) as response:
            return json.loads(response.read())

    # ===========================
    # 主生成方法 (流程编排)
    # ===========================

    def generate_image(
        self,
        prompt: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs
    ) -> bytes:
        """执行图片生成主流程"""
        self.validate_config()

        # 1. 准备参数
        width = kwargs.get('width', self.default_width)
        height = kwargs.get('height', self.default_height)
        aspect_ratio = kwargs.get('aspect_ratio')
        
        # 根据宽高比调整尺寸 (覆盖直接传入的宽高)
        if aspect_ratio:
            ar_map = {'1:1': (1024, 1024), '16:9': (1024, 576), '9:16': (576, 1024), '3:4': (768, 1024), '4:3': (1024, 768)}
            if aspect_ratio in ar_map:
                width, height = ar_map[aspect_ratio]

        logger.info(f"准备生成: 尺寸={width}x{height}, 模式={self.prompt_mode}")

        # 2. 准备工作流
        workflow = copy.deepcopy(self.workflow_template)
        
        # 3. 适配并设置提示词
        adapted_prompt = self._adapt_prompt(
            prompt, 
            page_type=kwargs.get('page_type', ''), 
            page_content=kwargs.get('page_content', '')
        )
        self._update_node(workflow, self.text_node_id, 'text', adapted_prompt)

        # 4. 设置种子和尺寸
        seed = random.randint(1, 2**31 - 1)
        self._update_node(workflow, self.seed_node_id, 'seed', seed)
        self._update_node(workflow, self.width_node_id, 'width', width)
        self._update_node(workflow, self.width_node_id, 'height', height)

        # 5. 执行生成与监控
        ws = None
        try:
            ws = self._connect_websocket()
            prompt_id = self._queue_prompt(workflow)
            logger.info(f"任务已提交: {prompt_id}, 开始监控...")
            
            self._monitor_execution(ws, prompt_id, progress_callback)
            
            # 6. 下载结果
            images = self._download_generated_images(prompt_id)
            if not images:
                raise Exception("工作流执行完成，但未产生图片输出")
            return images[0] # 返回第一张图

        except Exception as e:
            logger.error(f"生成失败: {e}")
            raise
        finally:
            if ws: ws.close()

    # ... (get_supported_sizes 等其他接口保持不变)
    def get_supported_sizes(self) -> List[str]:
        return ['512x512', '768x1024', '1024x1024', '1024x768', '1024x576']

    def get_supported_aspect_ratios(self) -> List[str]:
        return ['1:1', '3:4', '4:3', '9:16', '16:9']