"""交互式入口：一个最简单的命令行对话循环，对应原项目里"用户发消息给 agent"这个真实入口。"""
from agent.agent_loop import step

AGENT_ID = "demo-agent"


def main():
    print("letta-memory-learn 演示（输入 exit 退出）")
    print(f"当前 agent_id = {AGENT_ID}\n")
    while True:
        # input(...)：Python 内置函数，暂停程序、从命令行读入用户输入的一行文本（返回字符串 str）
        # .strip()：字符串(str)自带的方法，去掉首尾的空白字符（空格、换行、制表符等）
        user_text = input("你: ").strip()
        # .lower()：字符串(str)的方法，把字符串整体转成小写，便于不区分大小写地比较
        if user_text.lower() in {"exit", "quit"}:
            break
        if not user_text:
            continue
        reply = step(AGENT_ID, user_text)
        print(f"助手: {reply}\n")


if __name__ == "__main__":
    main()
