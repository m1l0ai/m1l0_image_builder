from builder.service.
import logging
import click


stdformatter = logging.Formatter('%(levelname)s: %(name)s: %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(stdformatter)

logger = logging.getLogger('m1l0')
logger.setLevel("INFO")
logger.addHandler(ch)

version = '1.0.0'
@click.version_option(version)

@click.group()
def main():
    """M1L0 Image Builder"""
    pass

@click.command()
def start():
    """Starts ImageBuilder service"""
    pass

main.add_command(start)