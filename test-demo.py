"""AI Panel Studio 完整演示脚本"""

import requests
import json
import time
import sys
import io

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_json(data, title=""):
    """打印 JSON 数据"""
    if title:
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"{'='*50}")
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    print("[AI Panel Studio] 演示")
    print("="*50)

    # 1. 测试 LLM 嘉宾生成
    print("\n[1/5] 生成嘉宾阵容...")
    resp = requests.post(f"{BASE_URL}/api/guests/generate", json={
        "topic": "远程办公 vs 现场办公",
        "expert_count": 3
    })
    guests = resp.json()
    print_json(guests, "嘉宾生成结果")

    if not guests.get("ok"):
        print("[X] 嘉宾生成失败")
        return

    host = guests["host"]
    experts = guests["experts"]

    # 2. 创建讨论
    print("\n[2/5] 创建讨论...")
    resp = requests.post(f"{BASE_URL}/api/discussions", json={
        "topic": "远程办公 vs 现场办公",
        "host": host,
        "experts": experts,
        "max_rounds": 2
    })
    disc = resp.json()
    print_json(disc, "讨论创建结果")

    disc_id = disc["discussion_id"]

    # 3. 确认阵容
    print("\n[3/5] 确认阵容并开始讨论...")
    resp = requests.post(f"{BASE_URL}/api/discussions/{disc_id}/confirm")
    print_json(resp.json(), "确认结果")

    # 4. 生成发言
    print("\n[4/5] 生成发言...")
    participants = disc["participants"]

    for p in participants:
        print(f"\n生成 {p['name']} 的发言...")
        resp = requests.post(
            f"{BASE_URL}/api/discussions/{disc_id}/generate-speech",
            params={"participant_id": p["id"]}
        )
        result = resp.json()
        print(f"  [OK] 发言ID: {result.get('speech_id')}")

    # 5. 获取最终状态
    print("\n[5/5] 获取讨论状态...")
    resp = requests.get(f"{BASE_URL}/api/discussions/{disc_id}/status")
    print_json(resp.json(), "讨论状态")

    # 获取完整讨论
    resp = requests.get(f"{BASE_URL}/api/discussions/{disc_id}")
    full_disc = resp.json()
    print_json(full_disc["speeches"], "所有发言")

    print("\n" + "="*50)
    print("[DONE] 演示完成！")
    print(f"[ID] 讨论ID: {disc_id}")
    print(f"[WEB] 前端地址: http://localhost:3000/studio/{disc_id}")
    print("="*50)

if __name__ == "__main__":
    main()
