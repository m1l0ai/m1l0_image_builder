from builder.service.imageservice import serve
import click
import logging

version = '1.0.0'
@click.version_option(version)

@click.command()
@click.option("--host", default="[::]", type=str)
@click.option("--port", default=50051, type=int)
def start(host, port):
    """Starts ImageBuilder service"""
    print("Starting ImageBuilder service on host {} port {} ...".format(host, port))
    serve(host, port)

if __name__ == "__main__":
    start()