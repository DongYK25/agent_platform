# agent_platform# 1. 创建项目目录和虚拟环境
mkdir agent_demo && cd agent_demo
uv venv

# 2. 安装脚手架（用 uv run 直接跑 pip，不用激活）
uv run pip install fastapi-scaff

# 3. 生成项目
uv run fastapi-scaff new .

# 4. 安装依赖
uv pip install -r requirements.txt

# 5. 启动（全程不用 activate）
uv run python runserver.py

# 学习记录
1.env中设置开发环境是dev，数据库等相关配置在这里配置