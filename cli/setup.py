from setuptools import setup, find_packages

setup(
    name="creaturegrc",
    version="2.0.0",
    description="CLI-driven GRC platform for infrastructure compliance",
    author="CreatureGRC Team",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "psycopg2-binary>=2.9.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
        "rich>=13.0.0",
        "tabulate>=0.9.0",
        "jinja2>=3.1.0",
        "anthropic>=0.18.0",
        "litellm>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "creaturegrc=creaturegrc.cli:main",
        ],
    },
    python_requires=">=3.11",
)
