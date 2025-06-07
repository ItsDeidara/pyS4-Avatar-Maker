from pathlib import Path
from .models import AvatarPackage, UserType, FTPConfig, BatchResult
from .utils import zip_files, convert_to_dds
import shutil
import json
import logging
from ftplib import FTP
from typing import List

logger = logging.getLogger("pys4_avatar_maker.services")

def process_avatar(pkg: AvatarPackage, tmp_dir: Path):
    try:
        tmp_dir.mkdir(exist_ok=True)
        base_img = pkg.image_path
        png_path = tmp_dir / 'avatar.png'
        shutil.copy(base_img, png_path)
        logger.info(f"Copied base image to {png_path}")
        sizes = [440, 260, 128, 64]
        dds_paths = []
        for size in sizes:
            dds_path = tmp_dir / f'avatar{size}.dds'
            convert_to_dds(png_path, dds_path, size)
            dds_paths.append(dds_path)
        files_to_zip = [png_path] + dds_paths
        if pkg.user_type == UserType.OFFLINE_ACTIVATED:
            online_json = tmp_dir / 'online.json'
            with open(online_json, 'w', encoding='utf-8') as f:
                json.dump({
                    "avatarUrl": "http://static-resource.np.community.playstation.net/avatar_xl/WWS_E/E0012_XL.png",
                    "firstName": "",
                    "lastName": "",
                    "pictureUrl": "https://image.api.np.km.playstation.net/images/?format=png&w=440&h=440&image=https%3A%2F%2Fkfscdn.api.np.km.playstation.net%2F00000000000008%2F000000000000003.png&sign=blablabla019501",
                    "trophySummary": "{\"level\":1,\"progress\":0,\"earnedTrophies\":{\"platinum\":0,\"gold\":0,\"silver\":0,\"bronze\":0}}",
                    "isOfficiallyVerified": "true"
                }, f)
            files_to_zip.append(online_json)
            logger.info(f"Created online.json for offline activated user at {online_json}")
        return files_to_zip
    except Exception as e:
        logger.error(f"Error processing avatar: {e}", exc_info=True)
        raise

def package_avatar(pkg: AvatarPackage, tmp_dir: Path):
    try:
        files = process_avatar(pkg, tmp_dir)
        zip_files(files, pkg.output_path)
        logger.info(f"Packaged avatar to {pkg.output_path}")
        # Robust cleanup: remove the entire tmp_dir and its contents
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error packaging avatar: {e}", exc_info=True)
        # Try to clean up even on error
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

def upload_via_ftp(ftp_cfg: FTPConfig, file_path: Path):
    try:
        with FTP() as ftp:
            ftp.connect(ftp_cfg.host, ftp_cfg.port)
            if ftp_cfg.username and ftp_cfg.password:
                ftp.login(ftp_cfg.username, ftp_cfg.password)
            else:
                ftp.login()
            ftp.cwd(ftp_cfg.upload_dir)
            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {file_path.name}', f)
            logger.info(f"Uploaded {file_path} to FTP {ftp_cfg.host}:{ftp_cfg.port}{ftp_cfg.upload_dir}")
    except Exception as e:
        logger.error(f"FTP upload failed for {file_path}: {e}", exc_info=True)
        raise

def process_batch_avatars(image_paths: List[Path], user_type: UserType, output_dir: Path, ftp_cfg: FTPConfig = None) -> BatchResult:
    output_files = []
    ftp_transferred = 0
    for img_path in image_paths:
        out_file = output_dir / (img_path.stem + '.xavatar')
        tmp_dir = output_dir / (img_path.stem + '_tmp')
        pkg = AvatarPackage(image_path=img_path, user_type=user_type, output_path=out_file)
        package_avatar(pkg, tmp_dir)
        output_files.append(out_file)
        if ftp_cfg:
            try:
                upload_via_ftp(ftp_cfg, out_file)
                ftp_transferred += 1
            except Exception:
                pass
    return BatchResult(total=len(image_paths), ftp_transferred=ftp_transferred, output_files=output_files) 