import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCardNames, type CardNameEntry } from '../../../api/correspondences';
import '../ReferenceTab.css';

export default function CardNamesSection() {
  const [filterText, setFilterText] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');

  const { data: cardNames = [], isLoading } = useQuery<CardNameEntry[]>({
    queryKey: ['card-names'],
    queryFn: getCardNames,
  });

  // Extract available languages
  const languages = useMemo(() => {
    const langs = new Set<string>();
    for (const entry of cardNames) {
      langs.add(entry.field_name);
    }
    return [...langs].sort();
  }, [cardNames]);

  // Auto-select first language
  if (languages.length > 0 && !selectedLanguage) {
    setSelectedLanguage(languages[0]);
  }

  // Group by archetype, show selected language
  const grouped = useMemo(() => {
    const map = new Map<string, Map<string, string>>();
    for (const entry of cardNames) {
      const key = entry.archetype || entry.card_name;
      if (!map.has(key)) map.set(key, new Map());
      map.get(key)!.set(entry.field_name, entry.field_value);
    }
    return map;
  }, [cardNames]);

  const filteredKeys = useMemo(() => {
    return [...grouped.keys()].filter(key => {
      if (!filterText) return true;
      const q = filterText.toLowerCase();
      if (key.toLowerCase().includes(q)) return true;
      const langs = grouped.get(key)!;
      for (const val of langs.values()) {
        if (val.toLowerCase().includes(q)) return true;
      }
      return false;
    });
  }, [grouped, filterText]);

  if (isLoading) {
    return (
      <div className="reference-section">
        <h2 className="reference-section__title">Card Names</h2>
        <p className="reference-section__hint">Loading...</p>
      </div>
    );
  }

  if (cardNames.length === 0) {
    return (
      <div className="reference-section">
        <h2 className="reference-section__title">Card Names</h2>
        <p className="reference-section__hint">
          No card name translations found. Card names in other languages are populated
          from custom fields on individual decks (e.g. "English Name", "German Name").
        </p>
      </div>
    );
  }

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Card Names</h2>
      <p className="reference-section__hint">
        Card names across languages, sourced from custom fields on your decks.
      </p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <select
          value={selectedLanguage}
          onChange={e => setSelectedLanguage(e.target.value)}
          style={{ minWidth: 180 }}
        >
          {languages.map(lang => (
            <option key={lang} value={lang}>{lang}</option>
          ))}
        </select>
        <input
          type="text"
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
          placeholder="Search..."
          style={{ maxWidth: 250, flex: 1 }}
        />
      </div>

      <div className="reference-section__card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-body)' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 600 }}>
                Card
              </th>
              <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {selectedLanguage || 'Translation'}
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredKeys.map(key => {
              const langs = grouped.get(key)!;
              const value = langs.get(selectedLanguage) || '';
              if (!value && selectedLanguage) return null;
              return (
                <tr key={key}>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-primary)', fontWeight: 500 }}>
                    {key}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-primary)' }}>
                    {value}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
