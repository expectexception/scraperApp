import logging
import os
import shutil
from pathlib import Path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from .utils import (
    backup_collections, 
    restore_collection, 
    list_local_backups,
    get_mongo_client,
    get_db_name
)
from scraper_manager.api import _require_dashboard_auth

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_collections(request):
    """List all collections in the database."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    try:
        client = get_mongo_client()
        db_name = get_db_name()
        db = client[db_name]
        collections = db.list_collection_names()
        
        # Sort collections - put 'jobs' and user-related ones at top
        priority = ['jobs', 'auth_user', 'scraped_url', 'scraper_config']
        sorted_collections = sorted(
            collections, 
            key=lambda x: (0 if any(p in x.lower() for p in priority) else 1, x)
        )
        
        return Response({"collections": sorted_collections})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_backup(request):
    """Trigger a backup of specified collections."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    collection_names = request.data.get('collections')
    try:
        result = backup_collections(collection_names)
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_backups(request):
    """List all local backups."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    try:
        backups = list_local_backups()
        return Response({"backups": backups})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def restore_backup(request):
    """Restore from a specific backup ID or uploaded file."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    backup_id = request.data.get('backup_id')
    collection_name = request.data.get('collection') # Optional specific collection
    drop_existing = request.data.get('drop_existing', False)
    
    if not backup_id:
        return Response({"error": "backup_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        backup_dir = Path(settings.BASE_DIR) / "backups" / backup_id
        if not backup_dir.exists():
            return Response({"error": "Backup not found"}, status=status.HTTP_404_NOT_FOUND)
        
        results = []
        if collection_name:
            file_path = backup_dir / f"{collection_name}.json.gz"
            if not file_path.exists():
                return Response({"error": f"Collection {collection_name} not in backup"}, status=status.HTTP_404_NOT_FOUND)
            results.append(restore_collection(file_path, collection_name, drop_existing))
        else:
            # Restore all in the backup
            for file_path in backup_dir.glob("*.json.gz"):
                name = file_path.name.split('.')[0]
                results.append(restore_collection(file_path, name, drop_existing))
                
        return Response({"results": results})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_backup(request, backup_id):
    """Delete a local backup folder."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    try:
        backup_dir = Path(settings.BASE_DIR) / "backups" / backup_id
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            return Response({"status": "success"})
        else:
            return Response({"error": "Backup not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
