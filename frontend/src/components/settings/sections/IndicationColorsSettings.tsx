/**
 * Settings → General → Birth & Name Card Colors: one color per role
 * for the journal's "Indicate Birth & Name Cards" feature. Unset
 * roles fall back to the system defaults (gold for birth roles,
 * violet for name roles).
 */
import { useQueryClient } from '@tanstack/react-query';
import { updateIndicationColors } from '../../../api/settings';
import {
  INDICATION_ROLES,
  defaultColorFor,
  useIndicationColors,
} from '../../../utils/indicationColors';
import { useToast } from '../../../context/ToastContext';
import './IndicationColorsSettings.css';

export default function IndicationColorsSettings() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { overrides, colorFor, ready } = useIndicationColors();

  const save = async (next: Record<string, string>) => {
    try {
      await updateIndicationColors(next);
      queryClient.invalidateQueries({ queryKey: ['indication-colors'] });
    } catch {
      showToast('Saving colors failed.');
    }
  };

  const setColor = (roleKey: string, color: string) => {
    save({ ...overrides, [roleKey]: color });
  };

  const resetAll = () => save({});

  if (!ready) return null;

  const systems: { system: 'birth' | 'name'; title: string }[] = [
    { system: 'birth', title: 'Birth cards' },
    { system: 'name', title: 'Name cards' },
  ];

  return (
    <section className="settings-tab__section">
      <h3 className="settings-tab__section-title">Birth &amp; Name Card Colors</h3>
      <p className="settings-tab__hint">
        The colors used when "Indicate Birth &amp; Name Cards" is on in
        a journal entry — each kind of card has its own. A card holding
        several roles wears the first role's frame with the second's
        inner ring.
      </p>
      {systems.map(({ system, title }) => (
        <div key={system} className="indication-colors__group">
          <div className="indication-colors__group-title">{title}</div>
          <div className="indication-colors__grid">
            {INDICATION_ROLES.filter(r => r.system === system).map(role => (
              <label key={role.key} className="indication-colors__row">
                <input
                  type="color"
                  value={colorFor(role.key)}
                  onChange={(e) => setColor(role.key, e.target.value)}
                />
                <span className="indication-colors__label">{role.label}</span>
                {overrides[role.key] &&
                  overrides[role.key] !== defaultColorFor(role.key) && (
                  <button
                    type="button"
                    className="indication-colors__reset"
                    title="Back to the default"
                    onClick={() => {
                      const next = { ...overrides };
                      delete next[role.key];
                      save(next);
                    }}
                  >
                    reset
                  </button>
                )}
              </label>
            ))}
          </div>
        </div>
      ))}
      {Object.keys(overrides).length > 0 && (
        <button type="button" onClick={resetAll}>
          Reset all to defaults
        </button>
      )}
    </section>
  );
}
