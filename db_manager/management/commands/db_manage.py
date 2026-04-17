import os
from django.core.management.base import BaseCommand, CommandError
from db_manager.utils import backup_collections, restore_collection, list_local_backups
from pathlib import Path

class Command(BaseCommand):
    help = 'Manage MongoDB backups and restores'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Backup collections')
        backup_parser.add_argument('--collections', nargs='+', help='Specific collections to backup')
        backup_parser.add_argument('--dir', help='Output directory')
        
        # Restore command
        restore_parser = subparsers.add_parser('restore', help='Restore from backup')
        restore_parser.add_argument('backup_id', help='ID of the backup (folder name)')
        restore_parser.add_argument('--collection', help='Specific collection to restore')
        restore_parser.add_argument('--drop', action='store_true', help='Drop existing collections before restoring')
        
        # List command
        subparsers.add_parser('list', help='List available local backups')

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            backups = list_local_backups()
            if not backups:
                self.stdout.write(self.style.WARNING("No backups found."))
                return
            
            self.stdout.write(self.style.SUCCESS("Available Backups:"))
            for b in backups:
                self.stdout.write(f"- {b['id']} ({b['timestamp']}) - {len(b['collections'])} collections, {b['size_bytes'] / (1024*1024):.2f} MB")
                
        elif action == 'backup':
            self.stdout.write("Starting backup...")
            result = backup_collections(options['collections'], options['dir'])
            self.stdout.write(self.style.SUCCESS(f"Backup created at: {result['path']}"))
            self.stdout.write(f"ID: {result['backup_id']}")
            for res in result['results']:
                status = self.style.SUCCESS("OK") if res['status'] == 'success' else self.style.ERROR("FAILED")
                self.stdout.write(f"  - {res['collection']}: {status} ({res.get('count', 0)} docs)")
                
        elif action == 'restore':
            backup_id = options['backup_id']
            base_dir = Path(os.getcwd()) / "backups"
            backup_dir = base_dir / backup_id
            
            if not backup_dir.exists():
                raise CommandError(f"Backup directory not found: {backup_dir}")
            
            self.stdout.write(f"Restoring from {backup_id}...")
            
            drop = options['drop']
            if options['collection']:
                file_path = backup_dir / f"{options['collection']}.json.gz"
                if not file_path.exists():
                    raise CommandError(f"Collection file {file_path} not found in backup")
                res = restore_collection(file_path, options['collection'], drop)
                self.stdout.write(self.style.SUCCESS(f"Restored {res['collection']}: {res['count']} documents"))
            else:
                for file_path in backup_dir.glob("*.json.gz"):
                    name = file_path.name.split('.')[0]
                    res = restore_collection(file_path, name, drop)
                    self.stdout.write(self.style.SUCCESS(f"Restored {res['collection']}: {res['count']} documents"))
                    
        else:
            self.print_help('manage.py', 'db_manage')
