import click
from builder.service.imageservice import serve


version = '1.0.0'
@click.version_option(version)

@click.command()
@click.option("--host", default="[::]", type=str, help="Hostname of service")
@click.option("--port", default=50051, type=int, help="Port for service")
@click.option("--secure", is_flag=True, help="Run service with TLS")
def start(host, port, secure):
    """Starts ImageBuilder service"""
    print("[INFO] Starting ImageBuilder service on host {} port {} ...".format(host, port))
    serve(host, port, secure)

if __name__ == "__main__":
    start()