import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCacheStats, clearCache } from '../../../api/settings';
import '../SettingsTab.css';
import { confirmDialog } from '../../common/ConfirmDialog';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function CacheSection() {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const { data: cacheStats } = useQuery({
    queryKey: ['cache-stats'],
    queryFn: getCacheStats,
  });

  const showMsg = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleClearCache = async () => {
    if (!(await confirmDialog('Clear the thumbnail cache? Thumbnails will be regenerated as needed.'))) return;
    try {
      await clearCache();
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] });
      showMsg('Cache cleared', 'success');
    } catch {
      showMsg('Failed to clear cache', 'error');
    }
  };

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">Thumbnail Cache</h2>

      {message && (
        <div className={`settings-tab__message settings-tab__message--${message.type}`}>
          {message.text}
        </div>
      )}

      <section className="settings-tab__section">
        {cacheStats && (
          <p className="settings-tab__cache-info">
            {cacheStats.count} thumbnails ({formatBytes(cacheStats.size_bytes)})
          </p>
        )}
        <button className="settings-tab__clear-cache-btn" onClick={handleClearCache}>
          Clear Cache
        </button>
      </section>
    </div>
  );
}
