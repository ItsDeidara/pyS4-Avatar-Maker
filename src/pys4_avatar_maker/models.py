from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

class UserType(Enum):
    LOCAL = 'local'
    OFFLINE_ACTIVATED = 'offline_activated'

@dataclass
class AvatarPackage:
    image_path: Path
    user_type: UserType
    output_path: Path

@dataclass
class FTPConfig:
    host: str
    port: int = 2121
    username: Optional[str] = None
    password: Optional[str] = None
    upload_dir: str = "/"

@dataclass
class BatchResult:
    total: int
    ftp_transferred: int
    output_files: List[Path] 