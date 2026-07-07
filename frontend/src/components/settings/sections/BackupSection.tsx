import { useState, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDefaults, createBackup, restoreBackup, getBackupStatus } from '../../../api/settings';
import '../SettingsTab.css';
import { confirmDialog } from '../../common/ConfirmDialog';

/** "today", "yesterday", "N days ago", or "never". */
function relativeDays(dateStr: string | null): string {
  if (!dateStr) return 'never';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'never';
  const dayMs = 24 * 60 * 60 * 1000;
  const startOfDay = (x: Date) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((startOfDay(new Date()) - startOfDay(d)) / dayMs);
  if (diff <= 0) return 'today';
  if (diff === 1) return 'yesterday';
  return `${diff} days ago`;
}

/** Days since the date, or Infinity if never. */
function daysSince(dateStr: string | null): number {
  if (!dateStr) return Infinity;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return Infinity;
  return (Date.now() - d.getTime()) / (24 * 60 * 60 * 1000);
}

export default function BackupSection() {
  const queryClient = useQueryClient();
  const [backingUp, setBackingUp] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [includeImages, setIncludeImages] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: defaults } = useQuery({
    queryKey: ['settings-defaults'],
    queryFn: getDefaults,
  });

  const { data: status } = useQuery({
    queryKey: ['backup-status'],
    queryFn: getBackupStatus,
  });

  // Deck scans only live in with-images backups (and the user's own
  // external backups), so nudge when that copy is aging.
  const imagesBackupStale = status ? daysSince(status.last_backup_with_images_time) > 30 : false;

  const showMsg = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleBackup = async () => {
    setBackingUp(true);
    try {
      const blob = await createBackup(includeImages);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tarot_backup_${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      queryClient.invalidateQueries({ queryKey: ['settings-defaults'] });
      queryClient.invalidateQueries({ queryKey: ['backup-status'] });
      showMsg('Backup created successfully', 'success');
    } catch (err) {
      console.error('Backup failed:', err);
      const detail = err instanceof Error ? err.message : String(err);
      showMsg(`Backup failed: ${detail}`, 'error');
    } finally {
      setBackingUp(false);
    }
  };

  const handleRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!(await confirmDialog({ message: 'Restore from backup? This will replace all current data. A safety backup will be created first.', title: 'Restore Backup', confirmLabel: 'Restore' }))) {
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    setRestoring(true);
    try {
      await restoreBackup(file);
      queryClient.invalidateQueries();
      showMsg('Backup restored successfully. Reload the page to see changes.', 'success');
    } catch {
      showMsg('Restore failed', 'error');
    } finally {
      setRestoring(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">Backup & Restore</h2>

      {message && (
        <div className={`settings-tab__message settings-tab__message--${message.type}`}>
          {message.text}
        </div>
      )}

      <section className="settings-tab__section">
        {status && (
          <div className="settings-tab__backup-status">
            <p className="settings-tab__backup-status-line">
              Automatic snapshot: <strong>{relativeDays(status.last_auto_snapshot)}</strong>
              {status.auto_snapshot_count > 0 && (
                <span className="settings-tab__backup-status-detail">
                  {' '}({status.auto_snapshot_count} kept, written on every launch)
                </span>
              )}
            </p>
            <p className="settings-tab__backup-status-line">
              Last manual backup: <strong>{relativeDays(status.last_backup_time)}</strong>
            </p>
            <p className={`settings-tab__backup-status-line${imagesBackupStale ? ' settings-tab__backup-status-line--warn' : ''}`}>
              Last backup including card images:{' '}
              <strong>{relativeDays(status.last_backup_with_images_time)}</strong>
              {imagesBackupStale && (
                <span className="settings-tab__backup-status-detail">
                  {' '}— your card scans are only protected by with-images backups;
                  consider making one
                </span>
              )}
            </p>
          </div>
        )}
        {!status && defaults?.last_backup_time && (
          <p className="settings-tab__last-backup">
            Last backup: {new Date(defaults.last_backup_time).toLocaleString()}
          </p>
        )}

        <div className="settings-tab__backup-row">
          <label className="settings-tab__checkbox-label">
            <input
              type="checkbox"
              checked={includeImages}
              onChange={(e) => setIncludeImages(e.target.checked)}
            />
            Include card images
          </label>
          <button
            className="settings-tab__backup-btn"
            onClick={handleBackup}
            disabled={backingUp}
          >
            {backingUp ? 'Creating...' : 'Create Backup'}
          </button>
        </div>

        <div className="settings-tab__restore-row">
          <button
            className="settings-tab__restore-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={restoring}
          >
            {restoring ? 'Restoring...' : 'Restore from Backup'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={handleRestore}
            style={{ display: 'none' }}
          />
        </div>
      </section>
    </div>
  );
}
