import docker
import os
import tarfile
import tempfile
from io import BytesIO
import time
import subprocess
import sys
from docker import APIClient

"""
import tarfile
import time
from io import BytesIO

example_data = 'example'
data = example_data.encode('utf-8')

tarstream = BytesIO()
tar = tarfile.TarFile(fileobj=tarstream, mode='w')
tarinfo = tarfile.TarInfo(name='example.txt')
tarinfo.size = len(data)
tarinfo.mtime = time.time()
tar.addfile(tarinfo, BytesIO(data))
tar.close()

tarstream.seek(0)
r = container.put_archive('/root/', tarstream)
"""

"""
# https://github.com/docker/docker-py/issues/1808

docker cp "/media/chee/DISK D/mlops/m1l0_trainerv2/examples" datavol-attached:/tmp/code/123

docker run -it --rm -v m1l0-builder:/tmp ubuntu:18.04
"""

# TODO: Below needs to be implemented on M1L0 client side
# The archive must be inside container volume before building...
def create_archive(tmp_code_path):
    """
    Creates and saves the archive at tmp code path

    https://github.com/docker/docker-py/issues/1808
    """
    tarstream = BytesIO()
    archive = tarfile.TarFile(fileobj=tarstream, mode="w")
    code_dir = os.path.split(tmp_code_path)[-1]

    for x in os.listdir(tmp_code_path):
        p = os.path.join(tmp_code_path, x)
        archive.add(p, arcname=os.path.join(".", x))

    archive.close()
    return tarstream


if __name__ == "__main__":

    client = docker.from_env()

    # create initial container to bind volume to
    data_dir = '/tmp'

    kwargs = {
        'name': 'datavol-attached',
        'auto_remove': True,
        'detach': True,
        'volumes': {
            'm1l0-builder': {'bind': data_dir, 'mode': 'rw'}
        },   
    }

    datavol_attached = client.containers.create(
        "ubuntu:18.04",
        # command="mkdir -p /tmp/code/mytestdata",
        # command="tail -f /dev/null",
        **kwargs
    )

    print(datavol_attached)

    local_path = "/media/chee/DISK D/mlops/m1l0_trainerv2/examples"

    cmd = [
        "docker",
        "cp",
        local_path,
        "datavol-attached:/tmp/code/mytestdata"
    ]

    cmd_str = " ".join(cmd)

    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT
    )

    exit_code = None
    while exit_code is None:
        stdout = process.stdout.readline().decode("utf-8")
        sys.stdout.write(stdout)
        exit_code = process.poll()

    datavol_attached.remove()



    # local_path = "/media/chee/DISK D/mlops/m1l0_trainerv2/examples"
    # tarstream = create_archive(local_path)
    # print(tarstream)
    # tarstream.seek(0)

    # datavol_attached.put_archive(path="/tmp/code/mytestdata/", data=tarstream)

    # resp = datavol_attached.stop()
    # print(resp)