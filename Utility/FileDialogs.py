from PyQt6.QtCore import QDir, QFileInfo
from PyQt6.QtWidgets import QFileDialog


def selectFileDialog(
    parent,
    for_saving: bool,
    instruction: str,
    start_dir: str = None,
    file_filter: str = '',
    multiple: bool = False
) -> None | str | list[str]:
    """
    Dialog window for selecting a file

    :param parent: parent widget
    :param for_saving: save (True) or open (False)
    :param instruction: instruction text
    :param start_dir: starting directory
    :param file_filter: (optional) filter for allowed files
    :param multiple: (optional) multiple files allowed

    :return: path as string (one file) or list of strings (multiple files) or None (no files)
    """

    full_file_paths = []
    if start_dir is None:
        start_dir = QDir.currentPath()

    if for_saving:
        full_file_path, _ = QFileDialog.getSaveFileName(parent, instruction, start_dir, file_filter)
        full_file_paths.append(full_file_path)

    else:
        if multiple:
            full_file_paths, _ = QFileDialog.getOpenFileNames(parent, instruction, start_dir, file_filter)

        else:
            full_file_path, _ = QFileDialog.getOpenFileName(parent, instruction, start_dir, file_filter)
            full_file_paths.append(full_file_path)

    file_names = []

    for full_file_path in full_file_paths:
        file_names.append(QFileInfo(full_file_path).filePath())
    if len(file_names) == 0:
        return None
    if len(file_names) == 1 and not multiple:
        return file_names[0]
    else:
        return file_names


def selectFolderDialog(
    parent,
    instruction: str,
    start_dir: str = None
) -> str:
    """
    Dialog window for selecting a folder

    :param parent: parent widget
    :param instruction: instruction text
    :param start_dir: starting directory

    :return: path as string or empty string (no folder)
    """

    if start_dir is None:
        start_dir = QDir.currentPath()

    return QFileDialog.getExistingDirectory(parent, instruction, start_dir)
