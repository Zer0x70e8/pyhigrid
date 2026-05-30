#
""""""

import os
import sys
import click
from pathlib import Path

src_path = Path(__file__).parent.parent  # 指向 .../src
sys.path.insert(0, str(src_path))
print("pwd:",
    os.getcwd()
)

@click.group()
@click.option('--db-path', default='media_library.db', help='数据库文件路径')
@click.option('--thumb-dir', default='./thumbs', help='缩略图保存目录')
@click.pass_context
def cli(ctx, db_path, thumb_dir):
    """pyhigrid 命令行工具"""
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db_path
    ctx.obj['thumb_dir'] = thumb_dir

from pyhigrid_cli.init_cmd import init
cli.add_command(init)
