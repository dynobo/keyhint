# Standard
from setuptools import setup, find_packages
from keyhint.core import __repo__, __version__, __author__, __email__

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="keyhint",
    version=__version__,
    description="Sample package",
    long_description=readme,
    author=__author__,
    author_email=__email__,
    url=__repo__,
    license=license,
    packages=find_packages(exclude=("tests", "data")),
)
