import subprocess
import sys
from pathlib import Path
import os

def build_exe():
    """
    Build a standalone executable using PyInstaller.
    Output will be in the 'dist' folder.
    Only the minimum runtime dependencies are included (see requirements.txt).
    """
    project_root = Path(__file__).parent.parent.parent
    run_py = project_root / 'run.py'
    icon_path = project_root / 'src' / 'pys4_avatar_maker' / 'default_avatar.png'
    add_data_arg = f"{icon_path}{os.pathsep}src/pys4_avatar_maker"
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name', 'pyS4_Avatar_Maker',
        '--hidden-import', 'imageio.plugins',
        '--add-data', add_data_arg,
        str(run_py)
    ]
    # If you have a .ico icon, add: '--icon', str(icon_path.with_suffix('.ico'))
    print(f"Running: {' '.join(map(str, cmd))}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    build_exe() 