from setuptools import setup, find_packages

setup(
    name="extraction_pipeline",
    version="7.0.0",
    description="Clean job requirements extraction pipeline",
    author="Arden & Team",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "openpyxl>=3.0.0", 
        "requests>=2.25.0",
        "pathlib",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'extract-jobs=extraction_pipeline.main:main',
        ],
    },
)
