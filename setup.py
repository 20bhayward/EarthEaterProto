from setuptools import setup, find_packages

setup(
    name="eartheater",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pygame>=2.0.0",
        "numpy>=1.20.0",
    ],
)