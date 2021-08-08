from builder.service.imageservice import serve
import click
import logging


stdformatter = logging.Formatter('%(levelname)s: %(name)s: %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(stdformatter)

logger = logging.getLogger('builder')
logger.setLevel("INFO")
logger.addHandler(ch)

version = '1.0.0'
@click.version_option(version)

@click.command()
@click.option("--host", default="[::]", type=str)
@click.option("--port", default=50051, type=int)
def start(host, port):
    """Starts ImageBuilder service"""
    serve(host, port)