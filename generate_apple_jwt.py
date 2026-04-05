#!/usr/bin/env python3
"""
生成 Apple Sign In JWT Token
用于 Supabase Apple Provider 配置

使用方法：
1. 将 .p8 文件放在同一目录
2. 修改下面的配置信息
3. 运行: python generate_apple_jwt.py
"""

import jwt
import time
import sys
from pathlib import Path

# ========== 配置信息 ==========
# 请修改以下信息为你的实际值

# Key ID（10位字符，从 Apple Developer 获取）
KEY_ID = '58Z4H63M2J'

# Team ID（10位字符，从 Apple Developer 获取）
TEAM_ID = 'S528T4D35V'

# Service ID（在 Apple Developer 中创建的 Service ID）
# 注意：对于 iOS 应用，如果 Supabase 配置使用 Bundle ID，这里也应该使用 Bundle ID
# 如果 Supabase 配置使用 Service ID，这里应该使用 Service ID
SERVICE_ID = 'com.irine.personal.StockReviewThree'  # 使用 Bundle ID

# .p8 文件路径（相对于此脚本的路径）
P8_FILE_PATH = 'AuthKey_58Z4H63M2J.p8'

# ========== 生成 JWT ==========

def generate_jwt():
    """生成 Apple Sign In JWT Token"""
    
    # 检查 .p8 文件是否存在
    p8_path = Path(__file__).parent / P8_FILE_PATH
    if not p8_path.exists():
        print(f"❌ 错误：找不到 .p8 文件: {p8_path}")
        print(f"   请确保文件存在，或修改 P8_FILE_PATH 变量")
        return None
    
    # 读取私钥
    try:
        with open(p8_path, 'r') as f:
            private_key = f.read()
    except Exception as e:
        print(f"❌ 错误：无法读取 .p8 文件: {e}")
        return None
    
    # 验证配置信息
    if KEY_ID == 'YOUR_KEY_ID_HERE' or TEAM_ID == 'YOUR_TEAM_ID_HERE' or SERVICE_ID == 'com.yourname.stockreview.web':
        print("❌ 错误：请先修改脚本中的配置信息（KEY_ID, TEAM_ID, SERVICE_ID）")
        return None
    
    # JWT Header
    headers = {
        'kid': KEY_ID,
        'alg': 'ES256'
    }
    
    # JWT Payload
    now = int(time.time())
    payload = {
        'iss': TEAM_ID,  # Issuer (Team ID)
        'iat': now,  # Issued at
        'exp': now + (86400 * 180),  # Expiration (6 months)
        'aud': 'https://appleid.apple.com',  # Audience
        'sub': SERVICE_ID  # Subject (Service ID)
    }
    
    try:
        # 生成 JWT
        token = jwt.encode(
            payload,
            private_key,
            algorithm='ES256',
            headers=headers
        )
        
        print("✅ JWT Token 生成成功！")
        print("\n" + "="*80)
        print("请复制以下 JWT Token 到 Supabase 的 Secret Key 字段：")
        print("="*80)
        print(token)
        print("="*80)
        print(f"\n有效期：6个月（从 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))} 开始）")
        print(f"过期时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['exp']))}")
        print("\n⚠️  注意：JWT token 过期后需要重新生成")
        
        return token
        
    except Exception as e:
        print(f"❌ 错误：生成 JWT 失败: {e}")
        print("\n可能的原因：")
        print("1. .p8 文件格式不正确")
        print("2. Key ID 或 Team ID 不正确")
        print("3. 缺少必要的 Python 库（运行: pip install PyJWT cryptography）")
        return None


if __name__ == '__main__':
    print("🍎 Apple Sign In JWT Token 生成器")
    print("="*80)
    print()
    
    # 检查依赖
    try:
        import jwt
    except ImportError:
        print("❌ 错误：缺少 PyJWT 库")
        print("   请运行: pip install PyJWT cryptography")
        sys.exit(1)
    
    generate_jwt()
