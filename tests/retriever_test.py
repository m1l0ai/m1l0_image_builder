import pytest
from builder.core.retriever import GetSourceFiles
from m1l0_services.imagebuilder.image_builder_pb2 import BuildRequest, BuildIgnores
import tempfile
import os
from pathlib import Path
import shutil

def test_non_existent_dir_raises_exception():
    request = BuildRequest(id="123", source="dir:///tmp/test")
    retriever = GetSourceFiles(request)

    # should raise exception of dir does not exist...
    with pytest.raises(Exception) as exc_info:
        retriever.call()

    assert str(exc_info.value) == "Directory /tmp/test does not exist!"

def test_dir_exists(create_tmp_directory):
    request = BuildRequest(id="123", source="dir:///tmp/test")
    retriever = GetSourceFiles(request)

    with create_tmp_directory("test", "123") as res:
        orig_dir, new_dir = res
        fpath = os.path.join(orig_dir, "hello")
        Path(fpath).touch()
        new_fpath = os.path.join(new_dir, 'hello')

        code_path = retriever.call()
        assert code_path == "/tmp/code/123"
        assert os.path.exists(new_dir) == True, "Moved to new directory"
        assert os.path.exists(new_fpath) == True, "Moved contents to new directory"

def test_dir_exists_with_ignores(create_tmp_directory):
    request = BuildRequest(id="123", source="dir:///tmp/test")

    for ig in ["*.txt", "__pycache__"]:
        ig2 = BuildIgnores(value=ig)
        request.ignores.append(ig2)

    retriever = GetSourceFiles(request)

    with create_tmp_directory("test", "123") as res:
        orig_dir, new_dir = res
        fpath = os.path.join(orig_dir, "hello.txt")
        dpath = os.path.join(orig_dir, "__pycache__")
        Path(fpath).touch()
        Path(dpath).mkdir(exist_ok=True)

        new_fpath = os.path.join(new_dir, 'hello.txt')
        new_dpath = os.path.join(new_dir, "__pycache__")

        code_path = retriever.call()
        assert code_path == "/tmp/code/123"
        assert os.path.exists(new_dir) == True, "Moved to new directory"
        assert os.path.exists(new_fpath) == False, "File should have been ignored"
        assert os.path.exists(new_dpath) == False, "Directory should have been ignored"