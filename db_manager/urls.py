from django.urls import path
from . import api

app_name = 'db_manager'

urlpatterns = [
    path('collections/', api.list_collections, name='list_collections'),
    path('backup/', api.create_backup, name='create_backup'),
    path('backups/', api.get_backups, name='get_backups'),
    path('backups/<str:backup_id>/', api.delete_backup, name='delete_backup'),
    path('restore/', api.restore_backup, name='restore_backup'),
]
