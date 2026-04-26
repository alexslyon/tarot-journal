import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCardCorrespondences, setCardOverrides, getFieldOptions, type FieldOption } from '../../api/correspondences';
import type { ResolvedCorrespondence } from '../../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';
import MultiValueSelect from '../common/MultiValueSelect';
import FreeTextValue from '../common/FreeTextValue';
import { expandNumerologyOnAdd } from '../../utils/numerology';
import './CardCorrespondences.css';

interface CardCorrespondencesProps {
  cardId: number;
}

export default function CardCorrespondences({ cardId }: CardCorrespondencesProps) {
  const queryClient = useQueryClient();

  const { data: correspondences = [] } = useQuery<ResolvedCorrespondence[]>({
    queryKey: ['card-correspondences', cardId],
    queryFn: () => getCardCorrespondences(cardId),
  });

  const { data: allFieldOptions = [] } = useQuery<FieldOption[]>({
    queryKey: ['field-options', 'all'],
    queryFn: () => getFieldOptions(),
  });

  // Group options by field_name
  const optionsByField = new Map<string, string[]>();
  for (const opt of allFieldOptions) {
    if (!optionsByField.has(opt.field_name)) optionsByField.set(opt.field_name, []);
    optionsByField.get(opt.field_name)!.push(opt.option_value);
  }

  const corrMap = new Map<string, ResolvedCorrespondence>();
  for (const c of correspondences) corrMap.set(c.field_name, c);

  const commitOverride = async (fieldName: string, values: string[]) => {
    const corr = corrMap.get(fieldName);
    const inheritedValues = corr?.source === 'inherited' ? corr.values : [];

    // If the user picked values that match the inherited set exactly, revert
    // (no override needed — inherit cleanly).
    const sorted = [...values].sort();
    const sortedInherited = [...inheritedValues].sort();
    const matchesInherited = JSON.stringify(sorted) === JSON.stringify(sortedInherited);

    try {
      if (values.length === 0 || matchesInherited) {
        await setCardOverrides(cardId, [{ field_name: fieldName, field_value: null }]);
      } else {
        await setCardOverrides(cardId, [{ field_name: fieldName, field_values: values }]);
      }
      queryClient.invalidateQueries({ queryKey: ['card-correspondences', cardId] });
    } catch (err) {
      console.error('Failed to save override:', err);
    }
  };

  const revertOverride = async (fieldName: string) => {
    try {
      await setCardOverrides(cardId, [{ field_name: fieldName, field_value: null }]);
      queryClient.invalidateQueries({ queryKey: ['card-correspondences', cardId] });
    } catch (err) {
      console.error('Failed to revert override:', err);
    }
  };

  return (
    <div className="card-corr">
      <div className="card-corr__grid">
        {CORRESPONDENCE_FIELDS.map(fieldName => {
          const corr = corrMap.get(fieldName);
          const values = corr?.values || [];
          const isOverride = corr?.source === 'override';
          const isInherited = corr?.source === 'inherited';
          const opts = optionsByField.get(fieldName) || [];

          return (
            <div key={fieldName} className="card-corr__field">
              <label className="card-corr__label">
                {CORRESPONDENCE_FIELD_LABELS[fieldName]}
                {isOverride && <span className="card-corr__badge card-corr__badge--override">override</span>}
                {isInherited && <span className="card-corr__badge card-corr__badge--inherited">inherited</span>}
              </label>
              <div className="card-corr__select-row">
                {fieldName === 'numerology' ? (
                  <FreeTextValue
                    values={values}
                    onCommit={vals => commitOverride(fieldName, expandNumerologyOnAdd(values, vals))}
                    compact
                  />
                ) : (
                  <MultiValueSelect
                    values={values}
                    options={opts}
                    onCommit={vals => commitOverride(fieldName, vals)}
                    compact
                  />
                )}
                {isOverride && (
                  <button
                    className="card-corr__revert-btn"
                    onClick={() => revertOverride(fieldName)}
                    title="Revert to inherited value"
                  >
                    Revert
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
