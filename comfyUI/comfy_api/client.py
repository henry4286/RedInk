# comfy_api/client.py
import json
import urllib.request
import urllib.parse
import websocket # 需要 pip install websocket-client
import uuid
import os
import sys
import time # 确保导入了 time 模块

class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.http_base = f"http://{self.server_address}"
        self.ws_base = f"ws://{self.server_address}/ws"
        self.client_id = str(uuid.uuid4())

    def _queue_prompt(self, prompt_workflow):
        """内部方法：向ComfyUI发送排队请求"""
        p = {"prompt": prompt_workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"{self.http_base}/prompt", data=data, method="POST")
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())

    def _get_image_content(self, filename, subfolder, folder_type):
        """内部方法：下载图片二进制数据"""
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"{self.http_base}/view?{url_values}") as response:
            return response.read()

    def _get_history(self, prompt_id):
        """内部方法：获取特定任务的历史记录"""
        with urllib.request.urlopen(f"{self.http_base}/history/{prompt_id}") as response:
            return json.loads(response.read())
            
    def _print_progress(self, value, total_steps):
        """内部方法：打印进度条"""
        if total_steps == 0:
            total_steps = 1
        percent = int((value / total_steps) * 100)
        bar_length = 30
        filled_length = int(bar_length * value // total_steps)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f"\r[ComfyUI进度] |{bar}| {percent}% ({value}/{total_steps})")
        sys.stdout.flush()

    def generate_image(self, workflow_json, save_dir="output"):
        """
        对外暴露的主要方法：执行工作流并返回生成的图片路径列表。
        它会阻塞直到图片生成完毕，实时显示进度，并统计耗时。
        """
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # --- NEW: 计时开始 ---
        start_time = time.time()
        # --------------------

        # 1. 建立 WebSocket 连接
        ws = websocket.WebSocket()
        try:
            ws.connect(f"{self.ws_base}?clientId={self.client_id}")
        except ConnectionRefusedError:
             print(f"\n[Error] 无法连接到 ComfyUI WebSocket: {self.ws_base}")
             print("请确认 ComfyUI 是否正在运行。")
             return []

        # 2. 发送工作流到队列
        try:
            prompt_response = self._queue_prompt(workflow_json)
            prompt_id = prompt_response['prompt_id']
            print(f"[ComfyUI] 任务已提交，ID: {prompt_id}，开始监听进度...")
        except urllib.error.URLError as e:
             print(f"\n[Error] 发送任务失败: {e}")
             ws.close()
             return []

        current_node_progress = 0
        total_node_progress = 0

        # 3. 循环监听 WebSocket 消息
        while True:
            try:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    msg_type = message['type']
                    data = message.get('data', {})
                    
                    if data.get('prompt_id') != prompt_id:
                        continue

                    if msg_type == 'progress':
                        current_node_progress = data['value']
                        total_node_progress = data['max']
                        self._print_progress(current_node_progress, total_node_progress)
                    
                    elif msg_type == 'execution_start':
                        sys.stdout.write(f"\n[ComfyUI状态] 正在执行节点: {data.get('node_type', 'Unknown Node')}")
                        sys.stdout.flush()
                        current_node_progress = 0

                    # --- 处理执行完成消息 ---
                    elif msg_type == 'executing':
                        # data['node'] 为 null 表示整个流程结束
                        if data['node'] is None:
                            # --- NEW: 计时结束并计算 ---
                            end_time = time.time()
                            elapsed_time = end_time - start_time
                            # --------------------------
                            
                            # 打印耗时信息，保留两位小数
                            print(f"\n[ComfyUI] 任务 {prompt_id} 全部执行完毕！耗时: {elapsed_time:.2f} 秒")
                            break # 退出监听循环
                else:
                    continue
            except websocket.WebSocketConnectionClosedException:
                 print("\n[Error] WebSocket 连接意外断开。")
                 break
            except Exception as e:
                 print(f"\n[Error] 监听过程中发生错误: {e}")
                 break

        ws.close()

        # 4. 获取任务历史，下载保存图片
        print("[ComfyUI] 正在处理生成结果...")
        try:
            history_data = self._get_history(prompt_id)
            if prompt_id not in history_data:
                 print(f"[Error] 未能获取到任务 {prompt_id} 的历史记录。")
                 return []
            
            history = history_data[prompt_id]
            saved_image_paths = []

            if 'outputs' in history:
                for node_id in history['outputs']:
                    node_output = history['outputs'][node_id]
                    if 'images' in node_output:
                        for image_info in node_output['images']:
                            filename = image_info['filename']
                            subfolder = image_info['subfolder']
                            folder_type = image_info['type']
                            
                            # print(f"[下载中] {filename}...") # 可以注释掉减少刷屏
                            image_data = self._get_image_content(filename, subfolder, folder_type)
                            
                            save_filename = f"{prompt_id}_{filename}"
                            save_path = os.path.join(save_dir, save_filename)
                            with open(save_path, 'wb') as f:
                                f.write(image_data)
                            saved_image_paths.append(save_path)
                            print(f"[已保存] {save_path}")
            return saved_image_paths
            
        except Exception as e:
             print(f"[Error] 下载或保存图片时出错: {e}")
             return []

# 辅助函数保持不变
def update_node_value(workflow_json, node_id, input_key, new_value):
    """
    修改工作流JSON中指定节点的值。
    """
    if node_id in workflow_json and 'inputs' in workflow_json[node_id]:
        if input_key in workflow_json[node_id]['inputs']:
            workflow_json[node_id]['inputs'][input_key] = new_value
        else:
             print(f"[Workflow Warning] 节点 [{node_id}] 中找不到输入项 [{input_key}]")
    else:
        print(f"[Workflow Warning] 找不到节点 ID: [{node_id}]")