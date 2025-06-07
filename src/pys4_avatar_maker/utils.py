import zipfile
from pathlib import Path
from typing import List
from PIL import Image
import imageio
import os
import logging

logger = logging.getLogger("pys4_avatar_maker.utils")

def zip_files(file_paths: List[Path], zip_path: Path):
    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in file_paths:
                zipf.write(file_path, arcname=file_path.name)
        logger.info(f"Created zip archive at {zip_path} with files: {[str(f) for f in file_paths]}")
    except Exception as e:
        logger.error(f"Failed to create zip archive {zip_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error zipping files: {e}") from e

def convert_to_dds(image_path: Path, dds_path: Path, size: int):
    try:
        img = Image.open(image_path).convert('RGBA').resize((size, size))
        img.save(dds_path.with_suffix('.png'))  # Save PNG for preview/debug
        imageio.imwrite(str(dds_path), img, format='DDS')
        logger.info(f"Converted {image_path} to DDS {dds_path} at size {size}x{size}")
    except Exception as e:
        logger.error(f"Failed to convert {image_path} to DDS {dds_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error converting to DDS: {e}") from e 