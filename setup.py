from setuptools import setup, find_packages
import os

# Read the long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="github-stars-search",
    version="0.1.0",
    author="Nicolás Iglesias",
    author_email="nfiglesias@gmail.com",
    description="A command-line tool to semantically search your starred GitHub repositories",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/github-stars-organizer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyGithub>=2.1.1",
        "requests>=2.31.0",
        "pysqlite3-binary>=0.5.0",
        "sqlite-vec>=0.1.1",
        "torch>=2.0.0",
        "sentence-transformers>=2.2.2",
        "python-dotenv>=1.0.0",
        "tqdm>=4.66.0",
    ],
    extras_require={
        "cpu": [
            "torch>=2.0.0",  # Will be installed from CPU-only index if specified
        ],
    },
    entry_points={
        "console_scripts": [
            "ghs=src.cli:main",
        ],
    },
    include_package_data=True,
)
