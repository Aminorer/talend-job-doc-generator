"""Package installer pour Talend Documentation Generator."""

from pathlib import Path

from setuptools import find_packages, setup

BASE_DIR = Path(__file__).parent
README = (BASE_DIR / "README.md").read_text(encoding="utf-8")
REQUIREMENTS = (BASE_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()


setup(
    name="talend-doc-gen",
    version="1.0.0",
    description="Générateur de documentation pour jobs Talend (CLI + Streamlit)",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Talend Doc Team",
    url="https://github.com/example/talend-job-doc-generator",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    py_modules=["main"],
    package_data={
        "talend_doc_gen_assets": ["config.yaml", "templates/*.md"],
    },
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=REQUIREMENTS,
    entry_points={
        "console_scripts": [
            "talend-doc-gen=main:main",
            "talend-doc-gen-ui=ui.streamlit_app:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
