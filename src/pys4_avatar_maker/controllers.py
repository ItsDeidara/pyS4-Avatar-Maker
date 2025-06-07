from pathlib import Path
from .models import AvatarPackage, UserType
from .services import package_avatar

def create_avatar_package(image_path: Path, user_type: UserType, output_path: Path, tmp_dir: Path):
    pkg = AvatarPackage(image_path=image_path, user_type=user_type, output_path=output_path)
    package_avatar(pkg, tmp_dir) 