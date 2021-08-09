import pytest
import tempfile
import os
from pathlib import Path
import shutil
import contextlib

@pytest.fixture()
def create_tmp_directory():
    """
    Fixture to simulate how the code retriever would create
    directories

    We first create the orig directory and then a new dir
    with the id inside the /tmp/code folder to match application
    logic
    """
    @contextlib.contextmanager
    def _create_tmp(name, id, **kwargs):
        try:
            tmp_folder = os.path.join(tempfile.gettempdir(), name)
            # Create the original directory
            os.makedirs(tmp_folder)
            # Simulates creating the new directory
            new_dir = os.path.join(tempfile.gettempdir(), "code", id)

            yield (tmp_folder, new_dir)
        finally:
            if os.path.exists(tmp_folder):
                shutil.rmtree(tmp_folder)
            shutil.rmtree(new_dir)

    return _create_tmp