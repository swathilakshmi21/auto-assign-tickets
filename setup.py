"""Setup script for Auto Ticket Assignment POC"""
from setuptools import setup, find_packages

setup(
    name="auto-ticket-assignment",
    version="1.0.0",
    description="AI-powered ticket assignment system with LLM reasoning",
    author="American Airlines IT Department",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "xlrd>=2.0.0",
        "streamlit>=1.28.0",
        "python-dotenv>=1.0.0",
        "openai>=1.0.0",
        "python-dateutil>=2.8.0",
    ],
    python_requires=">=3.8",
)

