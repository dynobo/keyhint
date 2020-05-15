"""Module definition."""

# standard
from setuptools import setup, find_packages  # type: ignore
import keyhint

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license_text = f.read()

setup(
    name="keyhint",
    version=keyhint.__version__,
    description="Display context sensitive keyboard shortcuts or other hints",
    keywords="shortcuts keybindings hints helper reminder",
    long_description=readme,
    long_description_content_type="text/markdown",
    author=keyhint.__author__,
    author_email=keyhint.__email__,
    url=keyhint.__repo__,
    license=license_text,
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    entry_points={"console_scripts": ["keyhint=keyhint.__main__:run"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ],
)
