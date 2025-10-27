#!/usr/bin/env python3
"""
测试LLM API的可访问性
"""

from openai import OpenAI
import time

def test_llm_connection():
    """测试LLM API连接"""
    print("="*80)
    print("测试LLM API连接")
    print("="*80)

    # API配置
    api_key = ""
    base_url = "http://10.88.3.81:8502"

    print(f"\n配置信息:")
    print(f"  API Key: {'(空)' if not api_key else '***'}")
    print(f"  Base URL: {base_url}")

    try:
        print(f"\n正在初始化OpenAI客户端...")
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        print(f"  ✅ 客户端初始化成功")

        # 测试1: 简单的对话
        print(f"\n{'='*80}")
        print(f"测试1: 简单对话 (超时60秒)")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            response = client.chat.completions.create(
                model="gpt-4",  # 可以根据实际情况修改
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, can you respond with 'Hi there!'?"}
                ],
                temperature=0.3,
                max_tokens=50,
                timeout=60  # 60秒超时
            )

            elapsed = time.time() - start_time

            print(f"\n✅ 请求成功！")
            print(f"  耗时: {elapsed:.2f} 秒")
            print(f"\n回复内容:")
            print(f"  {response.choices[0].message.content}")
            print(f"\nAPI响应详情:")
            print(f"  模型: {response.model}")
            print(f"  完成原因: {response.choices[0].finish_reason}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ 请求失败！")
            print(f"  耗时: {elapsed:.2f} 秒")
            print(f"  错误类型: {type(e).__name__}")
            print(f"  错误信息: {str(e)}")
            return False

        # 测试2: 简单的代码分析任务
        print(f"\n{'='*80}")
        print(f"测试2: 代码分析任务 (超时60秒)")
        print(f"{'='*80}")

        test_prompt = """Analyze this simple C code snippet and tell me what it does in one sentence:

```c
int add(int a, int b) {
    return a + b;
}
```"""

        start_time = time.time()

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a code analysis expert."},
                    {"role": "user", "content": test_prompt}
                ],
                temperature=0.3,
                max_tokens=100,
                timeout=60
            )

            elapsed = time.time() - start_time

            print(f"\n✅ 请求成功！")
            print(f"  耗时: {elapsed:.2f} 秒")
            print(f"\n回复内容:")
            print(f"  {response.choices[0].message.content}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ 请求失败！")
            print(f"  耗时: {elapsed:.2f} 秒")
            print(f"  错误类型: {type(e).__name__}")
            print(f"  错误信息: {str(e)}")
            return False

        print(f"\n{'='*80}")
        print(f"✅ 所有测试通过！LLM API可正常访问")
        print(f"{'='*80}")
        return True

    except Exception as e:
        print(f"\n❌ 客户端初始化失败！")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {str(e)}")
        return False

def test_different_models():
    """测试不同的模型名称"""
    print(f"\n{'='*80}")
    print(f"测试不同的模型名称")
    print(f"{'='*80}")

    api_key = ""
    base_url = "http://10.88.3.81:8502"

    client = OpenAI(api_key=api_key, base_url=base_url)

    # 常见的模型名称
    models_to_test = [
        "gpt-4",
        "gpt-3.5-turbo",
        "qwen",
        "deepseek",
        "chatglm",
    ]

    print(f"\n尝试不同的模型名称:")

    for model_name in models_to_test:
        print(f"\n尝试模型: {model_name}")
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": "Reply with 'OK'"}
                ],
                max_tokens=10,
                timeout=30
            )
            print(f"  ✅ {model_name} 可用")
            print(f"     回复: {response.choices[0].message.content}")
            return model_name  # 返回第一个可用的模型
        except Exception as e:
            print(f"  ❌ {model_name} 不可用: {str(e)[:100]}")

    return None

if __name__ == "__main__":
    print("\n" + "="*80)
    print("LLM API 连接测试工具")
    print("="*80)

    # 主测试
    success = test_llm_connection()

    if not success:
        print("\n主测试失败，尝试测试不同的模型名称...")
        available_model = test_different_models()

        if available_model:
            print(f"\n建议使用的模型: {available_model}")
        else:
            print(f"\n所有模型测试都失败了。")
            print(f"\n可能的原因:")
            print(f"  1. API服务未启动或无法访问")
            print(f"  2. 网络连接问题")
            print(f"  3. 端口配置错误")
            print(f"  4. 需要正确的API密钥")
            print(f"\n建议:")
            print(f"  1. 检查服务是否在 http://10.88.3.81:8502 运行")
            print(f"  2. 尝试 curl http://10.88.3.81:8502/v1/models 查看可用模型")
            print(f"  3. 检查防火墙设置")

    print("\n测试完成。")
