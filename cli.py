# cli.py - 统一的命令行入口
import click
from app.core.app_factory import create_app
from app.services.media_manager import MediaManager
from app.config.log_config import configure_logging

@click.group()
def cli():
    """Media Management CLI"""
    configure_logging()

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def add_charts(env):
    """Add charts to database"""
    with create_app(env).app_context():
        MediaManager().add_charts_to_db()

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def update_playlists(env):
    """Update playlists"""
    with create_app(env).app_context():
        MediaManager().update_playlists()

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def remove_duplicates(env):
    """Remove duplicate media files"""
    with create_app(env).app_context():
        MediaManager().remove_duplicates()

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def cleanup_missing(env):
    """Remove entries for missing files"""
    with create_app(env).app_context():
        MediaManager().cleanup_missing_files()

if __name__ == '__main__':
    cli()