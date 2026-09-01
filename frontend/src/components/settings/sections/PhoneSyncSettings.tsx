import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getPhoneSyncStatus,
  setPhoneSyncEnabled,
  startPhonePairing,
  unpairPhone,
} from '../../../api/settings';
import QueryError from '../../common/QueryError';
import './PhoneSyncSettings.css';

/**
 * Settings → General → Phone Sync.
 *
 * Controls the companion-app sync: an on/off switch for the LAN
 * listener (takes effect on next app start), pairing-code display,
 * and unpairing. Everything here talks to loopback-only endpoints.
 */
export default function PhoneSyncSettings() {
  const queryClient = useQueryClient();
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [restartNote, setRestartNote] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: status, isError, refetch } = useQuery({
    queryKey: ['phone-sync-status'],
    queryFn: getPhoneSyncStatus,
  });

  const handleToggle = async (enabled: boolean) => {
    setError(null);
    try {
      await setPhoneSyncEnabled(enabled);
      setRestartNote(true);
      queryClient.invalidateQueries({ queryKey: ['phone-sync-status'] });
    } catch {
      setError('Failed to save the phone sync setting.');
    }
  };

  const handleShowCode = async () => {
    setError(null);
    try {
      const res = await startPhonePairing();
      setPairingCode(res.code);
      queryClient.invalidateQueries({ queryKey: ['phone-sync-status'] });
    } catch {
      setError('Failed to generate a pairing code.');
    }
  };

  const handleUnpair = async () => {
    setError(null);
    try {
      await unpairPhone();
      setPairingCode(null);
      queryClient.invalidateQueries({ queryKey: ['phone-sync-status'] });
    } catch {
      setError('Failed to unpair.');
    }
  };

  return (
    <section className="settings-tab__section">
      <h3 className="settings-tab__section-title">Phone Sync</h3>
      <p className="settings-tab__hint">
        Lets the iPhone companion app connect over your home Wi-Fi to
        sync journal entries, reference text, and favorite decks. When
        off, the app is only reachable from this computer.
      </p>

      {isError && <QueryError what="phone sync status" onRetry={refetch} />}

      {status && (
        <>
          <div className="settings-tab__field">
            <label className="settings-tab__checkbox-label">
              <input
                type="checkbox"
                checked={status.enabled}
                onChange={(e) => handleToggle(e.target.checked)}
              />
              <span>Enable phone sync</span>
            </label>
            {restartNote && (
              <p className="settings-tab__hint phone-sync__restart-note">
                Takes effect the next time the app starts.
              </p>
            )}
          </div>

          <div className="settings-tab__field">
            {status.paired ? (
              <div className="phone-sync__paired-row">
                <span>
                  Paired with <strong>{status.device_name || 'a phone'}</strong>
                </span>
                <button onClick={handleUnpair}>Unpair</button>
              </div>
            ) : (
              <p className="settings-tab__hint">No phone paired yet.</p>
            )}
          </div>

          <div className="settings-tab__field">
            <button onClick={handleShowCode} disabled={!status.enabled}>
              Show pairing code
            </button>
            {!status.enabled && (
              <p className="settings-tab__hint">
                Turn on phone sync (and restart the app) before pairing.
              </p>
            )}
            {pairingCode && (
              <div className="phone-sync__code-box">
                <span className="phone-sync__code">{pairingCode}</span>
                <p className="settings-tab__hint">
                  Enter this code on the phone within 5 minutes. Pairing a
                  new phone replaces the old pairing.
                </p>
              </div>
            )}
          </div>
        </>
      )}

      {error && <p className="phone-sync__error">{error}</p>}
    </section>
  );
}
