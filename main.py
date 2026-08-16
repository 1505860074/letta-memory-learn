"""交互式入口：一个最简单的命令行对话循环，对应原项目里"用户发消息给 agent"这个真实入口。"""
from agent.agent_loop import step

AGENT_ID = "demo-agent"


def main():
    print("letta-memory-learn 演示（输入 exit 退出）")
    print(f"当前 agent_id = {AGENT_ID}\n")
    while True:
        user_text = input("你: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        if not user_text:
            continue
        reply = step(AGENT_ID, user_text)
        print(f"助手: {reply}\n")


if __name__ == "__main__":
    main()
