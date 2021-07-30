import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(HERE, "README.md")) as f:
    README = f.read()

setup(
    name="m1l0-builder",
    version="1.0.0",
    description="M1L0 Image Builder",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/m1l0",
    author="Chee Yeo",
    author_email="ckyeo.1@gmail.com",
    license="MIT",
    packages=find_packages(exclude=[
        'tests', 
        'tests.*',
        '__pycache__'
    ]),
    include_package_data=True,
    package_data={
        "builder": [
            "templates/image.jinja"
        ]
    },
    install_requires=[
        "docker~=5.0.0",
        "click==7.1.1",
        "Jinja2~=2.11",
        "grpcio-tools~=1.30"
    ],
    setup_requires=['pytest-runner', 'flake8'],
    tests_require=['pytest'],
    entry_points={
        # 'console_scripts': [
        #     'm1l0_builder=builder.cli:main'
        # ]
    },
)