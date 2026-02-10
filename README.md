# 简易 OJ 测试平台

一个类似洛谷的轻量代码测试系统（教学/原型用途）：

- 录入题目（标题、描述、时间限制）
- 配置测试点（输入 / 期望输出）
- 在线提交 Python 代码并逐点判题
- 提供简单前端界面

## 运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

访问 `http://localhost:5000`。

## 说明

- 当前版本只支持 Python 判题。
- 判题逻辑使用本地子进程执行代码，仅适合本地可信环境，不可直接用于公网生产。
