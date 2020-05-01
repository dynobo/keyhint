# Standard
from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="sample",
    version="0.1.0",
    description="Sample package",
    long_description=readme,
    author="Dynobo",
    author_email="dynobo@mailbox.org",
    url="https://github.com/dynobo/.template-python-module",
    license=license,
    packages=find_packages(exclude=("tests", "docs")),
)
