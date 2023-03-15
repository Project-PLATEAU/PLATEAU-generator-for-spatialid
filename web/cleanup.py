import argparse
import datetime
import os
import shutil

ROOT_DIR = os.path.dirname(__file__)
TEMP_DIR = os.environ.get('VIEWER_TEMP', os.path.join(ROOT_DIR, 'temp'))
LIFETIME = 1


def main(lifetime: int = LIFETIME):
    """cleanup old files

    Args:
        lifetime (int, optional): lifetime in hours. Defaults to LIFETIME.
    """
    lifetime_seconds = lifetime * 60 * 60
    for entry in os.listdir(TEMP_DIR):
        entry_path = os.path.join(TEMP_DIR, entry)
        if not os.path.isdir(entry_path):
            continue
        modified = int(os.stat(entry_path).st_mtime)
        now = int(datetime.datetime.now().timestamp())
        if now - modified > lifetime_seconds:
            shutil.rmtree(entry_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lifetime', type=int, default=LIFETIME, help='lifetime in hours')
    args = parser.parse_args()
    main(
        lifetime=args.lifetime
    )
