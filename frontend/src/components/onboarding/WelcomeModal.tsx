import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import { createProfile } from '../../api/profiles';
import { updateDefaults } from '../../api/settings';
import { setOnboardingFlags } from '../../api/onboarding';
import type { TabId } from '../layout/TabNav';
import './WelcomeModal.css';

interface WelcomeModalProps {
  open: boolean;
  onClose: () => void;
  onGoTo: (tab: TabId) => void;
}

/**
 * First-run welcome: one screen, one job — create the user's own
 * Reader profile (and set it as default), or point them at the
 * import flows if they were sent files. Closing it in any way marks
 * it done; it never reappears.
 */
export default function WelcomeModal({ open, onClose, onGoTo }: WelcomeModalProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [birthTime, setBirthTime] = useState('');
  const [birthPlace, setBirthPlace] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const finish = async () => {
    try {
      await setOnboardingFlags({ welcome_done: true });
    } catch {
      // Non-fatal: worst case the welcome shows once more.
    }
    onClose();
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('A name is all that’s required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await createProfile({
        name: name.trim(),
        birth_date: birthDate || null,
        birth_time: birthTime || null,
        birth_place_name: birthPlace || null,
      });
      await updateDefaults({ default_reader: created.id });
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      queryClient.invalidateQueries({ queryKey: ['settings-defaults'] });
      await finish();
    } catch {
      setError('Could not create the profile — try again?');
    } finally {
      setSaving(false);
    }
  };

  const goImport = async (tab: TabId) => {
    await finish();
    onGoTo(tab);
  };

  return (
    <Modal open={open} onClose={finish} title="Welcome to Tarot Journal" width={520}>
      <div className="welcome">
        <p className="welcome__lede">
          This is a home for your decks and your readings. It won&rsquo;t
          interpret cards for you &mdash; it keeps your practice organized
          and beautiful. Let&rsquo;s start with who you are.
        </p>

        <div className="welcome__form">
          <label className="welcome__label">
            Your name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="How you'd like to appear as reader"
              autoFocus
            />
          </label>
          <div className="welcome__birth-row">
            <label className="welcome__label">
              Birth date
              <input type="date" value={birthDate}
                     onChange={(e) => setBirthDate(e.target.value)} />
            </label>
            <label className="welcome__label">
              Birth time
              <input type="time" value={birthTime}
                     onChange={(e) => setBirthTime(e.target.value)} />
            </label>
          </div>
          <label className="welcome__label">
            Birth place
            <input
              type="text"
              value={birthPlace}
              onChange={(e) => setBirthPlace(e.target.value)}
              placeholder="City name (optional)"
            />
          </label>
          <p className="welcome__hint">
            Birth details are optional &mdash; they unlock birth cards and
            astrology charts later, and you can add them any time in
            Profiles.
          </p>
        </div>

        {error && <p className="welcome__error">{error}</p>}

        <div className="welcome__shared">
          <span className="welcome__shared-label">Were you sent files to start from?</span>
          <button onClick={() => goImport('library')}>Import a deck</button>
          <button onClick={() => goImport('spreads')}>Import spreads</button>
        </div>

        <div className="welcome__footer">
          <ModalCancelButton>Skip for now</ModalCancelButton>
          <button className="primary" onClick={handleCreate} disabled={saving}>
            {saving ? 'Creating…' : 'Create my profile'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
