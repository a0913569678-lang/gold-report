# -*- coding: utf-8 -*-
"""
企业微信群机器人 Webhook 推送长图。
用法：python notify.py （需设置环境变量 WECOM_WEBHOOK）
发图方式：base64 + md5，无需图床、无需可信 IP/域名。
"""
import os
import sys
import base64
import hashlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def send_image(webhook_url, image_path):
    """群机器人发图片（base64 + md5）。返回响应 JSON。"""
    try:
        import requests
        with open(image_path, "rb") as f:
            image_data = f.read()

        # 群机器人图片消息：base64 编码 + md5 值
        image_base64 = base64.b64encode(image_data).decode("ascii")
        image_md5 = hashlib.md5(image_data).hexdigest()

        payload = {
            "msgtype": "image",
            "image": {"base64": image_base64, "md5": image_md5},
        }
        resp = requests.post(webhook_url, json=payload, timeout=60)
        return resp.json()
    except Exception as e:
        print(f"[发送异常] {e}")
        return None


def main():
    webhook_url = os.environ.get("WECOM_WEBHOOK")
    if not webhook_url:
        print("[跳过] 未设置 WECOM_WEBHOOK 环境变量")
        return
    if not os.path.exists("gold_report.png"):
        print("[跳过] 未找到 gold_report.png")
        return

    # 检查图片大小（群机器人 base64 限制约 2MB）
    size = os.path.getsize("gold_report.png")
    if size > 1_500_000:
        print(f"[警告] 图片 {size/1024:.0f}KB 偏大，可能超过群机器人限制")
    else:
        print(f"[信息] 图片大小 {size/1024:.0f}KB，正常")

    print(">>> 发送长图到企业微信群 ...")
    result = send_image(webhook_url, "gold_report.png")
    if result and result.get("errcode") == 0:
        print("[发送成功] 长图已推送到企业微信群")
    else:
        print(f"[发送失败] {result}")


if __name__ == "__main__":
    main()
