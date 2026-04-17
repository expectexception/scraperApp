import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useAuth } from '../hooks/useAuth';
import { 
    Database,
    Trash2, 
    RefreshCcw, 
    CheckSquare, 
    Square, 
    Archive,
    History,
    AlertTriangle,
    Loader2,
    FileJson
} from 'lucide-react';
import { formatDate } from '../services/utils';
import { useDatabase as useDatabaseHook } from '../hooks/useScrapers';

export const DatabasePage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const { 
        collections, 
        backups, 
        createBackup, 
        restoreBackup, 
        deleteBackup 
    } = useDatabaseHook(isLoggedIn);

    const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
    const [isRestoring, setIsRestoring] = useState<string | null>(null);
    const [restoreModal, setRestoreModal] = useState<{ backupId: string; collections: string[] } | null>(null);
    const [restoreSelection, setRestoreSelection] = useState<string[]>([]);

    const toggleCollection = (name: string) => {
        if (selectedCollections.includes(name)) {
            setSelectedCollections(selectedCollections.filter(c => c !== name));
        } else {
            setSelectedCollections([...selectedCollections, name]);
        }
    };

    const selectAll = () => {
        if (collections.data) {
            setSelectedCollections(collections.data);
        }
    };

    const selectNone = () => {
        setSelectedCollections([]);
    };

    const toggleRestoreCollection = (name: string) => {
        if (restoreSelection.includes(name)) {
            setRestoreSelection(restoreSelection.filter(c => c !== name));
        } else {
            setRestoreSelection([...restoreSelection, name]);
        }
    };

    const selectAllRestore = () => {
        if (restoreModal?.collections) {
            setRestoreSelection(restoreModal.collections);
        }
    };

    const handleBackup = () => {
        createBackup.mutate(selectedCollections.length > 0 ? selectedCollections : undefined);
    };

    const handleRestore = (backup: any) => {
        // Open restore modal with collections to select
        setRestoreModal({ backupId: backup.id, collections: backup.collections });
        setRestoreSelection(backup.collections); // Default: select all
    };

    const confirmRestore = () => {
        if (!restoreModal) return;
        
        if (restoreSelection.length === 0) {
            alert('Please select at least one collection to restore.');
            return;
        }

        if (window.confirm(`Are you sure you want to restore ${restoreSelection.length} collection(s) from ${restoreModal.backupId}? This will overwrite existing data.`)) {
            setIsRestoring(restoreModal.backupId);
            
            // If all collections selected, don't pass collection param (faster full restore)
            if (restoreSelection.length === restoreModal.collections.length) {
                restoreBackup.mutate({ backupId: restoreModal.backupId, dropExisting: true }, {
                    onSettled: () => {
                        setIsRestoring(null);
                        setRestoreModal(null);
                    }
                });
            } else {
                // Restore each selected collection individually
                let completed = 0;
                restoreSelection.forEach((collection) => {
                    restoreBackup.mutate(
                        { backupId: restoreModal.backupId, collection, dropExisting: true },
                        {
                            onSettled: () => {
                                completed++;
                                if (completed === restoreSelection.length) {
                                    setIsRestoring(null);
                                    setRestoreModal(null);
                                }
                            }
                        }
                    );
                });
            }
        }
    };

    const handleDelete = (backupId: string) => {
        if (window.confirm(`Delete backup ${backupId}?`)) {
            deleteBackup.mutate(backupId);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tighter">Database Management</h1>
                    <p className="text-secondary text-sm font-medium">Backup and restore your collection data</p>
                </div>
                <div className="flex gap-2">
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        className="gap-2"
                        onClick={() => {
                            collections.refetch();
                            backups.refetch();
                        }}
                    >
                        <RefreshCcw className={`w-4 h-4 ${(collections.isFetching || backups.isFetching) ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Backup Section */}
                <Card 
                    className="xl:col-span-2"
                    title="Collection Backup" 
                    subtitle="Select specific collections or leave empty for full backup"
                    footer={
                        <div className="flex justify-between items-center w-full">
                            <span className="text-xs text-secondary font-medium">
                                {selectedCollections.length > 0 
                                    ? `${selectedCollections.length} collections selected` 
                                    : 'Full backup selected'}
                            </span>
                            <Button 
                                className="gap-2 shadow-glow-primary"
                                onClick={handleBackup}
                                isLoading={createBackup.isPending}
                            >
                                <Archive className="w-4 h-4" />
                                Run Backup Now
                            </Button>
                        </div>
                    }
                >
                    <div className="mb-4 flex flex-wrap gap-2">
                        <Button variant="ghost" size="xs" onClick={selectAll} className="text-[10px] font-bold uppercase tracking-widest">Select All</Button>
                        <Button variant="ghost" size="xs" onClick={selectNone} className="text-[10px] font-bold uppercase tracking-widest">Clear Selection</Button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                        {collections.isLoading ? (
                            Array.from({ length: 9 }).map((_, i) => (
                                <div key={i} className="h-10 bg-white/5 rounded-xl animate-pulse" />
                            ))
                        ) : collections.data?.map(coll => (
                            <button
                                key={coll}
                                onClick={() => toggleCollection(coll)}
                                className={`flex items-center gap-3 p-3 rounded-xl border transition-all text-left ${
                                    selectedCollections.includes(coll)
                                        ? 'bg-primary/10 border-primary/50 text-white shadow-glow-primary/10'
                                        : 'bg-white/[0.02] border-white/5 text-secondary hover:border-white/20'
                                }`}
                            >
                                {selectedCollections.includes(coll) ? (
                                    <CheckSquare className="w-4 h-4 text-primary" />
                                ) : (
                                    <Square className="w-4 h-4" />
                                )}
                                <span className={`text-xs font-bold truncate ${selectedCollections.includes(coll) ? 'text-white' : ''}`}>
                                    {coll}
                                </span>
                            </button>
                        ))}
                    </div>

                    {!collections.isLoading && !collections.data?.length && (
                        <div className="py-20 text-center">
                            <Database className="w-12 h-12 text-white/10 mx-auto mb-4" />
                            <p className="text-secondary font-medium">No collections found in database.</p>
                        </div>
                    )}
                </Card>

                {/* Info Card */}
                <div className="space-y-6">
                    <Card title="Restoration Guide" className="bg-gradient-to-br from-white/[0.02] to-primary/5">
                        <div className="space-y-4">
                            <div className="flex gap-4">
                                <div className="w-8 h-8 rounded-lg bg-warning/20 flex items-center justify-center shrink-0">
                                    <AlertTriangle className="w-4 h-4 text-warning" />
                                </div>
                                <div>
                                    <h4 className="text-xs font-black text-white uppercase tracking-wider mb-1">Destructive Operation</h4>
                                    <p className="text-[11px] text-secondary leading-relaxed">
                                        Restoring will overwrite existing data in the target collections. Always take a fresh backup before restoring.
                                    </p>
                                </div>
                            </div>
                            <div className="flex gap-4">
                                <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
                                    <FileJson className="w-4 h-4 text-primary" />
                                </div>
                                <div>
                                    <h4 className="text-xs font-black text-white uppercase tracking-wider mb-1">BSON Format</h4>
                                    <p className="text-[11px] text-secondary leading-relaxed">
                                        Data is exported in BSON-serialized JSON with GZIP compression for maximum fidelity and minimum size.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </Card>

                    <Card title="System Info">
                        <div className="space-y-3">
                            <div className="flex justify-between text-xs">
                                <span className="text-secondary">Engine</span>
                                <span className="text-white font-bold">MongoDB</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-secondary">Local Storage</span>
                                <span className="text-white font-bold">./backups</span>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>

            {/* Backups List */}
            <Card 
                title="Local Backup History" 
                subtitle="Stored on the server for quick access"
                icon={History}
            >
                <div className="overflow-x-auto -mx-6">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-white/5">
                                <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Backup ID</th>
                                <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Collections</th>
                                <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Size</th>
                                <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Date</th>
                                <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {backups.isLoading ? (
                                <tr>
                                    <td colSpan={5} className="py-12 text-center">
                                        <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
                                    </td>
                                </tr>
                            ) : backups.data?.map(backup => (
                                <tr key={backup.id} className="group hover:bg-white/[0.02] transition-colors">
                                    <td className="py-4 px-6 font-mono text-xs text-white">
                                        <div className="flex items-center gap-2">
                                            <Archive className="w-3.5 h-3.5 text-secondary" />
                                            {backup.id}
                                        </div>
                                    </td>
                                    <td className="py-4 px-6">
                                        <div className="flex flex-wrap gap-1">
                                            {backup.collections.slice(0, 3).map((c: string) => (
                                                <Badge key={c} variant="neutral" className="text-[9px] py-0 px-1.5">{c}</Badge>
                                            ))}
                                            {backup.collections.length > 3 && (
                                                <span className="text-[9px] text-secondary font-bold">+{backup.collections.length - 3} more</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="py-4 px-6 text-xs text-secondary">
                                        {(backup.size_bytes / (1024 * 1024)).toFixed(2)} MB
                                    </td>
                                    <td className="py-4 px-6 text-xs text-secondary">
                                        {formatDate(backup.timestamp)}
                                    </td>
                                    <td className="py-4 px-6 text-right">
                                        <div className="flex justify-end gap-2">
                                            <Button 
                                                size="xs" 
                                                variant="secondary"
                                                className="gap-1 px-3"
                                                onClick={() => handleRestore(backup)}
                                                isLoading={isRestoring === backup.id}
                                                disabled={!!isRestoring}
                                            >
                                                <RefreshCcw className="w-3 h-3" />
                                                Restore
                                            </Button>
                                            <Button 
                                                size="xs" 
                                                variant="danger"
                                                className="gap-1 px-3 hover:shadow-glow-danger"
                                                onClick={() => handleDelete(backup.id)}
                                            >
                                                <Trash2 className="w-3 h-3" />
                                                Delete
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {!backups.isLoading && !backups.data?.length && (
                                <tr>
                                    <td colSpan={5} className="py-12 text-center text-secondary text-sm italic">
                                        No local backups found. Secure your data by creating one.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* Restore Modal */}
            {restoreModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-2xl font-bold text-white">Restore from Backup</h2>
                                <p className="text-secondary text-sm mt-1">{restoreModal.backupId}</p>
                            </div>
                            <button
                                onClick={() => setRestoreModal(null)}
                                className="text-secondary hover:text-white transition-colors"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="bg-warning/10 border border-warning/30 rounded-lg p-4 mb-6 flex gap-3">
                            <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
                            <div>
                                <h4 className="text-sm font-bold text-warning mb-1">Destructive Operation</h4>
                                <p className="text-xs text-secondary">
                                    Restoring will overwrite existing data in the selected collections. This action cannot be undone.
                                </p>
                            </div>
                        </div>

                        <div className="mb-6">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="font-bold text-white text-sm">Select Collections to Restore</h3>
                                <span className="text-xs text-secondary font-medium">
                                    {restoreSelection.length} of {restoreModal.collections.length} selected
                                </span>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                                {restoreModal.collections.map(coll => (
                                    <button
                                        key={coll}
                                        onClick={() => toggleRestoreCollection(coll)}
                                        className={`flex items-center gap-2 p-3 rounded-lg border transition-all text-left text-xs font-medium ${
                                            restoreSelection.includes(coll)
                                                ? 'bg-primary/10 border-primary/50 text-white shadow-glow-primary/10'
                                                : 'bg-white/[0.02] border-white/5 text-secondary hover:border-white/20'
                                        }`}
                                    >
                                        {restoreSelection.includes(coll) ? (
                                            <CheckSquare className="w-4 h-4 text-primary" />
                                        ) : (
                                            <Square className="w-4 h-4" />
                                        )}
                                        <span className="truncate">{coll}</span>
                                    </button>
                                ))}
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    variant="ghost"
                                    size="xs"
                                    onClick={selectAllRestore}
                                    className="text-[10px] font-bold uppercase tracking-widest"
                                >
                                    Select All
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="xs"
                                    onClick={() => setRestoreSelection([])}
                                    className="text-[10px] font-bold uppercase tracking-widest"
                                >
                                    Clear
                                </Button>
                            </div>
                        </div>

                        <div className="flex gap-3 justify-end">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setRestoreModal(null)}
                                disabled={restoreBackup.isPending}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="secondary"
                                size="sm"
                                className="gap-2"
                                onClick={confirmRestore}
                                isLoading={restoreBackup.isPending}
                            >
                                <RefreshCcw className="w-4 h-4" />
                                Restore {restoreSelection.length} Collection{restoreSelection.length !== 1 ? 's' : ''}
                            </Button>
                        </div>
                    </Card>
                </div>
            )}
        </div>
    );
};
