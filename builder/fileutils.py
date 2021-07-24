import tempfile
import tarfile
import os

def simple_tar(path):
    """
    For uploading local files into docker volume using put_archive
    """
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)

    abs_path = os.path.abspath(path)
    t.add(abs_path, arcname=os.path.basename(path), recursive=False)

    t.close()
    f.seek(0)
    return f