import click
from builder.service.imageservice import serve

version = '1.0.0'


@click.version_option(version)
@click.command()
@click.option("--host", default="[::]", type=str)
@click.option("--port", default=50051, type=int)
@click.option("--secure", is_flag=True, help="Run service with TLS")
def start(host, port, secure):
    """Starts ImageBuilder service"""
    serve(host, port, secure)
