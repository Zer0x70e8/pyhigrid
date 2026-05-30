#
""""""

import click
import sqlite3
from pathlib import Path
from click import Command

# 定位 schema 文件位置（相对于当前文件）
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / 'resources/sql/media_library_schema.sql'
# 如果你的项目结构不同，可以改成 pkg_resources 等方式定位

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

@click.command('init')
@click.option('--db-path', required=True, help='目标数据库路径')
def init(db_path):
    """创建数据库表结构"""
    init_db(db_path)
    click.echo(f"数据库已创建: {db_path}")

init: Command