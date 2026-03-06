#!/usr/bin/env python3
"""
阿里云 NLS 测试脚本

验证阿里云 AK/SK 凭证是否有效，测试 Token 获取和语音识别功能。
可独立运行，仅依赖 requests 和 aliyun-python-sdk-core。

用法:
  python aliyun_nls_test.py
"""

import os
import sys
import json
import time
import struct
import math
import requests
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 尝试导入阿里云 SDK
try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
except ImportError:
    print("❌ 错误: 阿里云 SDK 未安装")
    print("请运行: pip install aliyun-python-sdk-core")
    sys.exit(1)


def get_env_or_input(env_var: str, prompt: str = "") -> str:
    """从环境变量或用户输入获取凭证"""
    value = os.getenv(env_var)
    if value:
        print(f"✓ {env_var} 已从环境/配置文件读取")
        return value
    
    if prompt:
        value = input(f"请输入 {prompt} ({env_var}): ").strip()
    
    if not value:
        raise ValueError(f"❌ {env_var} 未设置，请在 .env 文件中配置或通过环境变量设置")
    
    return value


def get_aliyun_token(ak_id: str, ak_secret: str, region: str = "cn-wuhan") -> dict:
    """获取阿里云 NLS Token"""
    print("\n[1/3] 正在获取阿里云访问令牌...")
    
    try:
        client = AcsClient(ak_id, ak_secret, region)
        
        request = CommonRequest()
        request.set_method("POST")
        request.set_domain(f"nls-meta.{region}.aliyuncs.com")
        request.set_version("2019-02-28")
        request.set_action_name("CreateToken")
        
        response = client.do_action_with_exception(request)
        token_data = json.loads(response)
        
        print(f"✅ Token 获取成功")
        print(f"   Token ID = {token_data['Token']['Id'][:32]}...")
        print(f"   过期时间 = {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(token_data['Token']['ExpireTime']))}")
        
        return token_data['Token']
        
    except Exception as e:
        print(f"❌ 获取 Token 失败: {e}")
        raise


def generate_test_pcm(duration_ms: int = 1000, sample_rate: int = 16000, frequency: int = 1000) -> bytes:
    """生成测试 PCM 音频（简单正弦波）"""
    print("\n[2/3] 正在生成测试音频...")
    
    # 计算采样点数
    num_samples = int(sample_rate * duration_ms / 1000)
    amplitude = 32767  # 16-bit PCM 最大值
    
    # 生成正弦波
    pcm_data = bytearray()
    for i in range(num_samples):
        # 正弦波: sin(2π * f * t)
        value = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
        # 16-bit 小端序编码
        pcm_data.extend(struct.pack('<h', value))
    
    print(f"✅ 已生成 {len(pcm_data)} 字节的测试音频 ({duration_ms}ms, {sample_rate}Hz, {frequency}Hz)")
    return bytes(pcm_data)


def recognize_audio(token_id: str, pcm_data: bytes, app_key: str, sample_rate: int = 16000, region: str = "cn-wuhan") -> dict:
    """调用阿里云一句话识别接口"""
    print("\n[3/3] 正在识别音频...")
    
    api_url = f"https://nls-gateway-{region}.aliyuncs.com/stream/v1/FlashRecognizer"
    
    params = {
        "appkey": app_key,
        "token": token_id,
        "format": "pcm",
        "sample_rate": sample_rate,
    }
    
    headers = {
        "Content-Type": "application/octet-stream"
    }
    
    try:
        response = requests.post(
            api_url,
            params=params,
            headers=headers,
            data=pcm_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            status_code = result.get("status")
            if status_code == 20000000:
                text = result.get("result", "")
                if text:
                    print(f"✅ 识别成功: \"{text}\"")
                else:
                    print(f"⚠️  识别结果为空")
            else:
                error_msg = result.get("message", "未知错误")
                print(f"❌ 识别失败 (status={status_code}): {error_msg}")
            
            return result
        else:
            print(f"❌ HTTP 错误: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"   响应: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        raise


def main():
    """主函数"""
    print("=" * 60)
    print("阿里云 NLS 测试脚本")
    print("=" * 60)
    
    try:
        # 1. 读取凭证
        print("\n[准备] 读取阿里云凭证...")
        ak_id = get_env_or_input("ALIYUN_ACCESS_KEY_ID", "AccessKey ID")
        ak_secret = get_env_or_input("ALIYUN_ACCESS_KEY_SECRET", "AccessKey Secret")
        app_key = get_env_or_input("ALIYUN_APP_KEY", "App Key")
        
        region = os.getenv("ALIYUN_REGION", "cn-wuhan")
        print(f"✓ 区域设置为: {region}")
        
        # 2. 获取 Token
        token_data = get_aliyun_token(ak_id, ak_secret, region)
        
        # 3. 生成测试音频
        test_pcm = generate_test_pcm(duration_ms=1000, sample_rate=16000)
        
        # 4. 识别音频
        result = recognize_audio(
            token_data['Id'],
            test_pcm,
            app_key,
            sample_rate=16000,
            region=region
        )
        
        print("\n" + "=" * 60)
        if result and result.get("status") == 20000000:
            print("✅ 测试通过！阿里云 NLS 服务正常使用")
        else:
            print("⚠️  测试完成，但识别失败或返回错误")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
