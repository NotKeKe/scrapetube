import re

from setuptools import setup, find_packages

with open("scrapetube/__init__.py", encoding="utf-8") as f:
    version = re.findall(r"__version__ = \"(.+)\"", f.read())[0]

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

with open("requirements.txt", encoding="utf-8") as f:
    requirements = [r.strip() for r in f]

setup(
    name="scrapetube",
    version=version,
    packages=find_packages(),
    include_package_data=True,
    url="https://github.com/NotKeKe/scrapetube",
    license="MIT",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Cheskel Twersky",
    # author_email="twerskycheskel@gmail.com",
    description="Scrape youtube without the official youtube api and without selenium.",
    keywords="youtube python channel videos search playlist list get",
    # classifiers=[
    #     "Programming Language :: Python :: 3",
    #     "License :: OSI Approved :: MIT License",
    #     "Operating System :: OS Independent",
    # ],
    # project_urls={"Documentation": "https://scrapetube.readthedocs.io/en/latest/"},
    install_requires=requirements,

    extras_require={
        "async": ["httpx>=0.24.0"]  # 當使用者指定 [async] 時，才會額外多裝這些套件
    },

    python_requires=">=3.6",
)
