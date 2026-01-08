import json
import os
import copy
# 导入我们封装的模块
from comfy_api.client import ComfyUIClient, update_node_value

# === 配置区域 (请根据你的实际情况修改) ===
COMFYUI_ADDRESS = "192.168.2.40:8188"
WORKFLOW_FILE = "workflow_api.json" # 你的API格式工作流文件路径

# 关键：你需要知道你的工作流中，哪个节点是负责输入提示词的。
# 打开你的 json 文件找到对应的节点 ID。
# 例如，如果你的提示词节点ID是 "6"，并且输入框的名字叫 "text" (大多数CLIP文本节点都是这样)
TEXT_NODE_ID = "57:45"       # 替换成你自己的提示词节点 ID (字符串)
TEXT_INPUT_NAME = "text" # 替换成该节点中接收文本的输入项名称

# (可选) 如果你想动态修改 Seed，找到 KSampler 节点的 ID
SEED_NODE_ID = "57:44"       # 替换成你自己的 KSampler 节点 ID
SEED_INPUT_NAME = "seed"
# ======================================


def load_workflow(file_path):
    """加载工作流JSON文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到工作流文件: {file_path}, 请确保你已经导出了 API 格式的 JSON。")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # 1. 初始化客户端
    client = ComfyUIClient(server_address=COMFYUI_ADDRESS)

    # 2. 加载工作流模板
    try:
        workflow_template = load_workflow(WORKFLOW_FILE)
    except Exception as e:
        print(f"错误: {e}")
        return

    # --- 开始第一次生成 ---
    print("\n--- 开始生成任务 1 ---")
    # 准备提示词
    prompt_text_1 = "A beautiful landscape rendering of a cyberpunk city street at night, neon lights, rain reflections, high detail, 8k."
    import random
    new_seed_1 = random.randint(1, 1000000000)

    # 深拷贝一份模板，避免修改污染原始模板
    workflow_1 = copy.deepcopy(workflow_template)

    # 使用辅助函数修改工作流参数
    # 修改提示词
    update_node_value(workflow_1, TEXT_NODE_ID, TEXT_INPUT_NAME, prompt_text_1)
    # (可选) 修改 Seed
    if SEED_NODE_ID:
         update_node_value(workflow_1, SEED_NODE_ID, SEED_INPUT_NAME, new_seed_1)

    # 调用客户端执行生成，并指定保存目录
    generated_images_1 = client.generate_image(workflow_1, save_dir="output/batch_1")
    print(f"任务 1 生成完成，结果保存在: {generated_images_1}")


    # --- 开始第二次生成 (演示模块复用) ---
    print("\n--- 开始生成任务 2 ---")
    prompt_text_2 = "A close-up photograph of a cute fluffy cat wearing sunglasses, sunny day, depth of field."
    new_seed_2 = random.randint(1, 1000000000)

    workflow_2 = copy.deepcopy(workflow_template)
    update_node_value(workflow_2, TEXT_NODE_ID, TEXT_INPUT_NAME, prompt_text_2)
    if SEED_NODE_ID:
         update_node_value(workflow_2, SEED_NODE_ID, SEED_INPUT_NAME, new_seed_2)

    generated_images_2 = client.generate_image(workflow_2, save_dir="output/batch_2")
    print(f"任务 2 生成完成，结果保存在: {generated_images_2}")

if __name__ == "__main__":
    # 确保 ComfyUI 已经运行
    # 确保 workflow_api.json 存在
    # 确保 TEXT_NODE_ID 配置正确
    main()