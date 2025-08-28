from setuptools import setup, find_packages

setup(
    name="athena-langchain",
    version="0.1.0",
    description="Athena LangChain integration for MCP",
    author="Athena Team",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.2.0",
        "langgraph>=0.2.30",
        "celery>=5.3",
        "kombu>=5.3",
        "python-dotenv>=1.0",
        "langchain-openai>=0.1.0",
        "langchain-community>=0.2.0",
        "redis>=5.0",
        "psycopg2-binary>=2.9",
        "langchain-text-splitters>=0.2.0",
        "pgvector>=0.2",
        "mcp>=0.1.0",
    ],
    python_requires=">=3.8",
)
