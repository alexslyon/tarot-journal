import { useState } from 'react';
import Modal, { ModalCancelButton } from '../common/Modal';
import { exportProfilePdf } from '../../api/pdfExport';
import { useToast } from '../../context/ToastContext';
import type { Profile } from '../../types';
import './ProfilePdfModal.css';

interface ProfilePdfModalProps {
  open: boolean;
  onClose: () => void;
  profile: Profile;
}

type MethodChoice = 'greer' | 'amberstone' | 'both';

export default function ProfilePdfModal({ open, onClose, profile }: ProfilePdfModalProps) {
  const { showToast } = useToast();
  const [exporting, setExporting] = useState(false);

  const chartPossible = Boolean(
    profile.birth_date
    && profile.birth_place_lat != null
    && profile.birth_place_lon != null,
  );
  const birthPossible = Boolean(profile.birth_date);
  const namePossible = Boolean(profile.full_name);

  const [includeChart, setIncludeChart] = useState(chartPossible);
  const [includeBirth, setIncludeBirth] = useState(birthPossible);
  const [method, setMethod] = useState<MethodChoice>('greer');
  const [includeName, setIncludeName] = useState(namePossible);

  const nothingSelected = !(includeChart && chartPossible)
    && !(includeBirth && birthPossible)
    && !(includeName && namePossible);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportProfilePdf(profile.id, {
        include_chart: includeChart && chartPossible,
        include_birth_cards: includeBirth && birthPossible,
        birth_card_methods: method === 'both' ? ['greer', 'amberstone'] : [method],
        include_name_cards: includeName && namePossible,
      });
      showToast('PDF downloaded');
      onClose();
    } catch (err) {
      console.error('Profile PDF export failed:', err);
      showToast('PDF export failed.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Export PDF — ${profile.name}`} width={480}>
      <div className="profile-pdf">
        <label className={`profile-pdf__option ${!chartPossible ? 'profile-pdf__option--disabled' : ''}`}>
          <input
            type="checkbox"
            checked={includeChart && chartPossible}
            disabled={!chartPossible}
            onChange={(e) => setIncludeChart(e.target.checked)}
          />
          <span>
            Natal chart
            {!chartPossible && (
              <em className="profile-pdf__hint">needs birth date and place</em>
            )}
          </span>
        </label>

        <label className={`profile-pdf__option ${!birthPossible ? 'profile-pdf__option--disabled' : ''}`}>
          <input
            type="checkbox"
            checked={includeBirth && birthPossible}
            disabled={!birthPossible}
            onChange={(e) => setIncludeBirth(e.target.checked)}
          />
          <span>
            Birth cards
            {!birthPossible && (
              <em className="profile-pdf__hint">needs a birth date</em>
            )}
          </span>
        </label>

        {includeBirth && birthPossible && (
          <div className="profile-pdf__methods">
            {([
              ['greer', 'Greer'],
              ['amberstone', 'Amberstone'],
              ['both', 'Both variants'],
            ] as [MethodChoice, string][]).map(([value, label]) => (
              <label key={value} className="profile-pdf__method">
                <input
                  type="radio"
                  name="pdf-birth-method"
                  checked={method === value}
                  onChange={() => setMethod(value)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        )}

        <label className={`profile-pdf__option ${!namePossible ? 'profile-pdf__option--disabled' : ''}`}>
          <input
            type="checkbox"
            checked={includeName && namePossible}
            disabled={!namePossible}
            onChange={(e) => setIncludeName(e.target.checked)}
          />
          <span>
            Name cards
            {!namePossible && (
              <em className="profile-pdf__hint">needs a Full Name</em>
            )}
          </span>
        </label>

        <div className="profile-pdf__footer">
          <ModalCancelButton>Cancel</ModalCancelButton>
          <button
            className="primary"
            onClick={handleExport}
            disabled={exporting || nothingSelected}
          >
            {exporting ? 'Exporting…' : 'Export PDF'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
