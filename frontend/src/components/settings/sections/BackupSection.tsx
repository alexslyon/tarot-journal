import { useState, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDefaults, createBackup, restoreBackup } from '../../../api/settings';
import '../SettingsTab.css';

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
      showMsg('Backup created successfully', 'success');
    } catch {
      showMsg('Backup failed', 'error');
    } finally {
      setBackingUp(false);
    }
  };

  const handleRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!window.confirm('Restore from backup? This will replace all current data. A safety backup will be created first.')) {
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
        {defaults?.last_backup_time && (
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
