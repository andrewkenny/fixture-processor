"""
This module contains useful file related functions
that can and will be used from anywhere in the program.
"""
import subprocess
import logging
from pathlib import Path


def open_folder(folder_path: Path):
    """
    This function opens up windows explorer
    at the path 'folder_path'
    """

    cmd = "explorer \"{}\"".format(str(folder_path))
    logging.info("subprocess.call is executing: %s", cmd)

    # os.system(cmd)
    subprocess.Popen(cmd)


def create_file_stub(file_path: Path, stub_text: str):
    """
    Used to create a user editable file. As such, to help
    the user, the file will aways start with a 'stub',
    which will tend to consist of some commented text,
    describing how to add entries to the file.

    if the file aready exists, this function does nothing.
    """

    if not file_path.exists():
        with file_path.open("w") as file_obj:
            file_obj.write(stub_text)


def open_file_for_editing(file_path: Path):
    """
    opens the provided filename with notepad.
    however uses notepad++ should it exist.
    """

    npp_path1 = Path(r"C:\Program Files (x86)\Notepad++\notepad++.exe")
    npp_path2 = Path(r"C:\Program Files\Notepad++\notepad++.exe")

    if npp_path1.exists():
        subprocess.Popen('{0} "{1}"'.format(str(npp_path1), str(file_path)))
        return

    if npp_path2.exists():
        subprocess.Popen('{0} "{1}"'.format(str(npp_path2), str(file_path)))
        return

    subprocess.Popen('{0} "{1}"'.format("notepad", str(file_path)))
