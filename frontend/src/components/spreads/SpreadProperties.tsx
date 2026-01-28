import { useQuery } from '@tanstack/react-query';
import { getCartomancyTypes } from '../../api/decks';
import { getDecks } from '../../api/decks';
import './SpreadProperties.css';

interface SpreadPropertiesProps {
  name: string;
  description: string;
  allowedDeckTypes: string[];
  defaultDeckId: number | null;
  onNameChange: (name: string) => void;
  onDescriptionChange: (desc: string) => void;
  onAllowedTypesChange: (types: string[]) => void;
  onDefaultDeckChange: (deckId: number | null) => void;
}

export default function SpreadProperties({
  name,
  description,
  allowedDeckTypes,
  defaultDeckId,
  onNameChange,
  onDescriptionChange,
  onAllowedTypesChange,
  onDefaultDeckChange,
}: SpreadPropertiesProps) {
  const { data: types = [] } = useQuery({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });

  const { data: decks = [] } = useQuery({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
  });

  const toggleType = (typeName: string) => {
    if (allowedDeckTypes.includes(typeName)) {
      onAllowedTypesChange(allowedDeckTypes.filter((t) => t !== typeName));
    } else {
      onAllowedTypesChange([...allowedDeckTypes, typeName]);
    }
  };

  return (
    <div className="spread-props">
      <div className="spread-props__field">
        <label className="spread-props__label">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="Spread name"
        />
      </div>

      <div className="spread-props__field">
        <label className="spread-props__label">Description</label>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          rows={3}
          placeholder="Describe the spread..."
        />
      </div>

      <div className="spread-props__field">
        <label className="spread-props__label">Allowed Deck Types</label>
        <div className="spread-props__hint">
          Leave all unchecked to allow any type.
        </div>
        <div className="spread-props__checks">
          {types.map((type) => (
            <label key={type.id} className="spread-props__check">
              <input
                type="checkbox"
                checked={allowedDeckTypes.includes(type.name)}
                onChange={() => toggleType(type.name)}
              />
              <span>{type.name}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="spread-props__field">
        <label className="spread-props__label">Default Deck</label>
        <select
          value={defaultDeckId ?? ''}
          onChange={(e) => onDefaultDeckChange(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">None</option>
          {decks.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
