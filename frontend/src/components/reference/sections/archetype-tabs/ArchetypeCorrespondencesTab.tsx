import { useState, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getCorrespondenceSystems,
  getSystemAssignments,
  setAssignmentValues,
  type Archetype,
} from '../../../../api/correspondences';
import { useToast } from '../../../../context/ToastContext';
import {
  CORRESPONDENCE_FIELDS,
  CORRESPONDENCE_FIELD_LABELS,
  type CorrespondenceSystem,
  type CorrespondenceAssignment,
} from '../../../../types';
import ArchetypeCardImage from './ArchetypeCardImage';
import './ArchetypeCorrespondencesTab.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
  onNavigateToSettings?: (
    section: string,
    payload?: { archetypeId?: number; fieldId?: number },
  ) => void;
}

const STORAGE_KEY = 'archetypes-viewer.correspondences.system';

export default function ArchetypeCorrespondencesTab({
  archetype,
  cartomancyType,
}: Props) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editing, setEditing] = useState(false);
  const { data: systems = [] } = useQuery<CorrespondenceSystem[]>({
    queryKey: ['correspondence-systems'],
    queryFn: getCorrespondenceSystems,
  });
  const matchingSystems = useMemo(
    () => systems.filter(s => (s.cartomancy_type || 'Tarot') === cartomancyType),
    [systems, cartomancyType],
  );

  const [systemId, setSystemId] = useState<number | null>(null);
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    const savedNum = saved ? Number(saved) : null;
    if (savedNum && matchingSystems.some(s => s.id === savedNum)) {
      setSystemId(savedNum);
    } else if (matchingSystems.length > 0) {
      setSystemId(matchingSystems[0].id);
    } else {
      setSystemId(null);
    }
  }, [matchingSystems]);
  useEffect(() => {
    if (systemId != null) localStorage.setItem(STORAGE_KEY, String(systemId));
  }, [systemId]);

  const { data: assignments = [] } = useQuery<CorrespondenceAssignment[]>({
    queryKey: ['system-assignments', systemId, archetype.id],
    queryFn: () => getSystemAssignments(systemId!, archetype.id),
    enabled: systemId != null,
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['system-assignments', systemId, archetype.id] });
    // Cards resolve correspondences through these systems — refresh
    // any open card views too.
    queryClient.invalidateQueries({ queryKey: ['card-correspondences'] });
  };

  // Group values by field, dedup, preserve insertion order.
  const valuesByField = useMemo(() => {
    const m = new Map<string, string[]>();
    for (const a of assignments) {
      if (!m.has(a.field_name)) m.set(a.field_name, []);
      const list = m.get(a.field_name)!;
      if (!list.includes(a.field_value)) list.push(a.field_value);
    }
    return m;
  }, [assignments]);

  const populatedFields = CORRESPONDENCE_FIELDS.filter(f =>
    (valuesByField.get(f) || []).length > 0,
  );

  if (matchingSystems.length === 0) {
    return (
      <div className="archetype-corr">
        <p className="archetype-corr__empty">
          No correspondence systems for {cartomancyType} yet. Create one in
          Settings → Correspondences.
        </p>
      </div>
    );
  }

  return (
    <div className="archetype-corr">
      <div className="archetype-corr__system-row">
        <label className="archetype-corr__label">System</label>
        <select
          value={systemId ?? ''}
          onChange={e => setSystemId(e.target.value ? Number(e.target.value) : null)}
        >
          {matchingSystems.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <button
          className="archetype-corr__edit-link"
          onClick={() => setEditing(e => !e)}
          disabled={systemId == null}
        >
          {editing ? 'Done editing' : 'Edit'}
        </button>
      </div>

      <div className="archetype-corr__body">
        <ArchetypeCardImage
          archetype={archetype}
          cartomancyType={cartomancyType}
        />
        <div className="archetype-corr__main">
          {editing && systemId != null ? (
            <div className="archetype-corr__editor">
              {CORRESPONDENCE_FIELDS.map(f => (
                <FieldEditorRow
                  key={`${systemId}-${archetype.id}-${f}`}
                  systemId={systemId}
                  archetypeId={archetype.id}
                  fieldName={f}
                  label={CORRESPONDENCE_FIELD_LABELS[f] || f}
                  initial={(valuesByField.get(f) || []).join(', ')}
                  onSaved={invalidate}
                  showToast={showToast}
                />
              ))}
              <p className="archetype-corr__hint">
                Several values? Separate them with commas.
              </p>
            </div>
          ) : populatedFields.length === 0 ? (
            <p className="archetype-corr__empty">
              No correspondence values set for {archetype.name} in this system.
            </p>
          ) : (
            <dl className="archetype-corr__list">
              {populatedFields.map(f => (
                <div key={f} className="archetype-corr__row">
                  <dt className="archetype-corr__field">
                    {CORRESPONDENCE_FIELD_LABELS[f] || f}
                  </dt>
                  <dd className="archetype-corr__values">
                    {(valuesByField.get(f) || []).join(', ')}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </div>
  );
}

/** One correspondence field in edit mode: comma-separated values in a
 *  text input, saved as a value list. */
function FieldEditorRow({
  systemId,
  archetypeId,
  fieldName,
  label,
  initial,
  onSaved,
  showToast,
}: {
  systemId: number;
  archetypeId: number;
  fieldName: string;
  label: string;
  initial: string;
  onSaved: () => void;
  showToast: (msg: string) => void;
}) {
  const [draft, setDraft] = useState(initial);
  const [saving, setSaving] = useState(false);
  const dirty = draft.trim() !== initial.trim();

  const handleSave = async () => {
    setSaving(true);
    try {
      const values = draft.split(',').map(v => v.trim()).filter(Boolean);
      await setAssignmentValues(systemId, archetypeId, fieldName, values);
      onSaved();
    } catch {
      showToast('Could not save the correspondence.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="archetype-corr__edit-row">
      <label className="archetype-corr__field">{label}</label>
      <input
        value={draft}
        onChange={e => setDraft(e.target.value)}
        placeholder="—"
      />
      <button onClick={handleSave} disabled={!dirty || saving}>
        {saving ? 'Saving…' : 'Save'}
      </button>
    </div>
  );
}
