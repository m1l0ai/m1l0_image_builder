import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

README_PATH = os.path.join(HERE, "README.md")
if os.path.exists(README_PATH):
    with open(README_PATH) as f:
        README = f.read()
else:
    README = "gRPC ImageBuilder service"

setup(
    name="m1l0-builder",
    version="1.0.0",
    description="gRPC service for building docker images",
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
        "click==8.0.1",
        "Jinja2~=2.11",
        "grpcio-tools~=1.30",
        "grpc-interceptor==0.12.0",
        "m1l0-protobufs~=0.9.0"
    ],
    entry_points={
        "console_scripts": [
            "builder = builder.cli.cli:start"
        ]
    },
    setup_requires=['pytest-runner', 'flake8'],
    tests_require=['pytest']
)