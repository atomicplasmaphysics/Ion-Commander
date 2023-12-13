import sys
from os import path, remove, listdir
from shutil import move, rmtree
from inspect import getfile, currentframe
from platform import system

import PyInstaller.__main__

current_dir = path.dirname(path.abspath(getfile(currentframe())))
parent_dir = path.dirname(current_dir)
sys.path.insert(0, parent_dir)


from Config.GlobalConf import GlobalConf

dist_path = f'{current_dir}/dist'
build_path = f'{current_dir}/build'


def clearFiles():
    """ Remove files (build- and dist-directories and any *.spec files) """
    directories = [f'{current_dir}/build', f'{current_dir}/dist']
    for directory in directories:
        if path.exists(directory):
            rmtree(directory)
    files = listdir(current_dir)
    files = [f'{current_dir}/{file}' for file in files if file.endswith('.spec')]
    for file in files:
        remove(file)


clearFiles()

# build app
hidden_imports = [
    'scipy.optimize'
]

exe_name = f'{GlobalConf.title}'
system_name = system()
if system_name == 'Windows':
    exe_name += '_windows.exe'
elif system_name == 'Linux':
    exe_name += '_linux'
elif system_name == 'Darwin':
    exe_name += '_mac.app'
else:
    exe_name += f'_{system_name.lower()}.exe'
divider = ';' if system_name == 'Windows' else ':'
pyinstaller_parameters = [
    f'{parent_dir}/main.py',
    f'--icon={parent_dir}/icons/logo.png',
    f'--name={exe_name}',
    '--windowed',
    '--clean',
    '--onefile',
    f'--distpath={dist_path}',
    f'--workpath={build_path}'
]

pyinstaller_parameters.extend([f'--hidden-import={hidden}' for hidden in hidden_imports])

PyInstaller.__main__.run(pyinstaller_parameters)

if path.exists(f'{current_dir}/dist/{exe_name}'):
    move(f'{current_dir}/dist/{exe_name}', f'{parent_dir}/{exe_name}')
    clearFiles()
    print('\n\nSUCCESSFULLY created executable file ')

else:
    print('\n\nERROR creating executable file')
