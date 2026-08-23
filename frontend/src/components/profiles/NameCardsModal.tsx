import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal from '../common/Modal';
import QueryError from '../common/QueryError';
import { CardTile } from './BirthCardsModal';
import {
  calculateNameCards,
  getNameCardsConfig,
  setNameCardsConfig,
  type NameRole,
  type YMode,
  type YOverride,
} from '../../api/nameCards';
import { cardThumbnailUrl } from '../../api/images';
import './NameCardsModal.css';

interface NameCardsModalProps {
  open: boolean;
  onClose: () => void;
  profileId: number;
  profileName: string;
  fullName: string;
}

/** Mirrors the calculator's default role rules so the selects show
 *  what will apply before the user overrides anything. */
function defaultRoles(count: number): NameRole[] {
  if (count <= 0) return [];   // pre-initialization: no parts yet
  if (count === 1) return ['first'];
  if (count === 2) return ['first', 'last'];
  return ['first', ...Array(count - 2).fill('middle') as NameRole[], 'last'];
}

function parseFullName(fullName: string): string[] {
  return fullName.trim().split(/\s+/).filter(Boolean);
}

export default function NameCardsModal({
  open,
  onClose,
  profileId,
  profileName,
  fullName,
}: NameCardsModalProps) {
  const queryClient = useQueryClient();

  // Working state — initialized from the saved config (or the parsed
  // full name) once per open.
  const [initialized, setInitialized] = useState(false);
  const [parts, setParts] = useState<string[]>([]);
  const [roles, setRoles] = useState<NameRole[] | null>(null);
  const [yMode, setYMode] = useState<YMode>('heuristic');
  const [yOverrides, setYOverrides] = useState<YOverride[]>([]);
  const [dropSuffixes, setDropSuffixes] = useState(true);

  const { data: saved } = useQuery({
    queryKey: ['name-cards-config', profileId],
    queryFn: () => getNameCardsConfig(profileId),
    enabled: open,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!open) { setInitialized(false); return; }
    if (initialized || !saved) return;
    const cfg = saved.config;
    setParts(cfg?.parts?.length ? cfg.parts : parseFullName(fullName));
    setRoles(cfg?.roles ?? null);
    setYMode(cfg?.y_mode ?? 'heuristic');
    setYOverrides(cfg?.y_overrides ?? []);
    setDropSuffixes(cfg?.drop_suffixes ?? true);
    setInitialized(true);
  }, [open, initialized, saved, fullName]);

  const persist = (next: {
    parts: string[]; roles: NameRole[] | null; yMode: YMode;
    yOverrides: YOverride[]; dropSuffixes: boolean;
  }) => {
    const isDefault = next.parts.join('\n') === parseFullName(fullName).join('\n')
      && next.roles === null && next.yMode === 'heuristic'
      && next.yOverrides.length === 0 && next.dropSuffixes;
    setNameCardsConfig(profileId, isDefault ? null : {
      parts: next.parts,
      roles: next.roles,
      y_mode: next.yMode,
      y_overrides: next.yOverrides,
      drop_suffixes: next.dropSuffixes,
    }).then(() => queryClient.invalidateQueries({
      queryKey: ['name-cards-config', profileId],
    })).catch(() => {});
  };

  const apply = (changes: Partial<{
    parts: string[]; roles: NameRole[] | null; yMode: YMode;
    yOverrides: YOverride[]; dropSuffixes: boolean;
  }>) => {
    const next = {
      parts, roles, yMode, yOverrides, dropSuffixes, ...changes,
    };
    setParts(next.parts);
    setRoles(next.roles);
    setYMode(next.yMode);
    setYOverrides(next.yOverrides);
    setDropSuffixes(next.dropSuffixes);
    persist(next);
  };

  const effectiveRoles = roles ?? defaultRoles(parts.length);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['name-cards', profileId, parts, roles, yMode, yOverrides, dropSuffixes],
    queryFn: () => calculateNameCards({
      parts,
      roles,
      y_mode: yMode,
      y_overrides: yOverrides,
      drop_suffixes: dropSuffixes,
      profile_id: profileId,
    }),
    enabled: open && initialized && parts.length > 0,
    staleTime: 30_000,
    retry: false,
  });

  const apiError = useMemo(() => {
    const detail = (error as { response?: { data?: { error?: string } } } | null)
      ?.response?.data?.error;
    return detail ?? null;
  }, [error]);

  const setPartText = (i: number, text: string) => {
    const next = [...parts];
    next[i] = text;
    // Letter indices may have shifted — stale Y overrides would flip
    // the wrong letter, so they reset when the text changes.
    apply({ parts: next, yOverrides: [] });
  };

  const setPartRole = (i: number, role: NameRole) => {
    const next = [...effectiveRoles];
    next[i] = role;
    apply({ roles: next });
  };

  const mergeLeft = (i: number) => {
    const next = [...parts];
    next[i - 1] = `${next[i - 1]} ${next[i]}`;
    next.splice(i, 1);
    apply({ parts: next, roles: null, yOverrides: [] });
  };

  const removePart = (i: number) => {
    const next = parts.filter((_, j) => j !== i);
    apply({ parts: next, roles: null, yOverrides: [] });
  };

  const addPart = () => {
    apply({ parts: [...parts, ''], roles: null, yOverrides: [] });
  };

  const resetToParsed = () => {
    apply({
      parts: parseFullName(fullName), roles: null, yMode: 'heuristic',
      yOverrides: [], dropSuffixes: true,
    });
  };

  const flipY = (part: number, index: number, current: 'vowel' | 'consonant') => {
    const flipped = current === 'vowel' ? 'consonant' : 'vowel';
    const rest = yOverrides.filter(o => !(o.part === part && o.index === index));
    apply({ yOverrides: [...rest, { part, index, as: flipped }] });
  };

  const c = data?.cards;
  const chordTiles = data && c ? [
    { card: c.first_name, caption: 'First name — Conscious Self' },
    { card: c.middle_name, caption: 'Middle name — Hidden Self' },
    { card: c.last_name, caption: 'Last name — Social Self' },
  ].filter(t => t.card != null) : [];

  return (
    <Modal open={open} onClose={onClose} title={`Name Cards — ${profileName}`} width={900}>
      <div className="name-cards birth-cards">
        {/* ── Name parts editor ── */}
        <div className="name-cards__parts">
          <div className="name-cards__parts-list">
            {parts.map((part, i) => (
              <div key={i} className="name-cards__part">
                {i > 0 && (
                  <button
                    className="name-cards__merge"
                    onClick={() => mergeLeft(i)}
                    title="Merge with the previous part (e.g. join a multi-word surname)"
                  >
                    ⇤
                  </button>
                )}
                <div className="name-cards__part-box">
                  <input
                    type="text"
                    className="name-cards__part-input"
                    value={part}
                    onChange={(e) => setPartText(i, e.target.value)}
                    placeholder="Name part"
                  />
                  <div className="name-cards__part-controls">
                    <select
                      className="name-cards__role"
                      value={effectiveRoles[i] ?? 'middle'}
                      onChange={(e) => setPartRole(i, e.target.value as NameRole)}
                    >
                      <option value="first">First</option>
                      <option value="middle">Middle</option>
                      <option value="last">Last</option>
                    </select>
                    {parts.length > 1 && (
                      <button
                        className="name-cards__part-remove"
                        onClick={() => removePart(i)}
                        title="Remove part"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <button className="name-cards__add-part" onClick={addPart}>+ Part</button>
          </div>
          <div className="name-cards__parts-tools">
            <label className="birth-cards__control">
              <span>Y counts as</span>
              <select
                value={yMode}
                onChange={(e) => apply({ yMode: e.target.value as YMode, yOverrides: [] })}
              >
                <option value="heuristic">Heuristic (per position)</option>
                <option value="always_vowel">Always vowel</option>
                <option value="always_consonant">Always consonant</option>
              </select>
            </label>
            <label className="name-cards__suffix-toggle">
              <input
                type="checkbox"
                checked={dropSuffixes}
                onChange={(e) => apply({ dropSuffixes: e.target.checked })}
              />
              <span>Ignore Jr / Sr / II / III</span>
            </label>
            <button className="name-cards__reset" onClick={resetToParsed}>
              Reset to parsed name
            </button>
          </div>
        </div>

        {isLoading && <div className="birth-cards__loading">Calculating…</div>}
        {isError && (apiError
          ? <div className="name-cards__api-error">{apiError}</div>
          : <QueryError what="name cards" onRetry={() => refetch()} />)}

        {data && c && (
          <>
            {(data.normalized || data.dropped_suffixes.length > 0) && (
              <p className="birth-cards__note">
                {data.normalized && 'Accents were removed for the calculation. '}
                {data.dropped_suffixes.length > 0
                  && `Ignored: ${data.dropped_suffixes.join(', ')}.`}
              </p>
            )}

            {data.y_positions.length > 0 && (
              <div className="name-cards__y-panel">
                {data.y_positions.map((y) => (
                  <button
                    key={`${y.part}-${y.index}`}
                    className={`name-cards__y-chip ${y.overridden ? 'name-cards__y-chip--overridden' : ''}`}
                    onClick={() => flipY(y.part, y.index, y.classified_as)}
                    title="Click to flip this Y between vowel and consonant"
                  >
                    Y in {parts[y.part] || `part ${y.part + 1}`} (letter {y.index + 1}):{' '}
                    <strong>{y.classified_as}</strong>
                  </button>
                ))}
              </div>
            )}

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Theme Chord</h3>
              <div className="birth-cards__row">
                {chordTiles.map((t) => (
                  <CardTile key={t.caption} card={t.card!} caption={t.caption} />
                ))}
              </div>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Inner & Outer</h3>
              <div className="birth-cards__row">
                {c.desires_inner_motivation && (
                  <CardTile
                    card={c.desires_inner_motivation}
                    caption="Desires & Inner Motivation (vowels)"
                  />
                )}
                {c.outer_persona && (
                  <CardTile card={c.outer_persona} caption="Outer Persona (consonants)" />
                )}
              </div>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Theme Note · Rhythm · Melody</h3>
              <div className="birth-cards__row">
                <CardTile card={c.theme_note} small caption="Theme Note" />
                <CardTile card={c.rhythm} small caption="Rhythm" />
                <CardTile card={c.melody} small caption="Melody" />
                {c.hidden_factor_name.map((card) => (
                  <CardTile key={card.number} card={card} small caption="Hidden Factor" />
                ))}
              </div>
              <p className="birth-cards__note">
                The same letters reduced at three different points — all three
                always land in the constellation of {data.shared_root}.
              </p>
            </div>

            {c.life_potential && (
              <div className="birth-cards__section">
                <h3 className="birth-cards__heading">Life Potential</h3>
                <div className="birth-cards__row">
                  <CardTile
                    card={c.life_potential}
                    caption="Name total + birth total, read at its most idealistic"
                  />
                </div>
              </div>
            )}

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Constellation Count</h3>
              <div className="name-cards__constellations">
                {Object.entries(data.constellation_count).map(([root, count]) => (
                  <div
                    key={root}
                    className={`name-cards__constellation ${count === 0 ? 'name-cards__constellation--absent' : ''} ${data.most_represented.includes(Number(root)) ? 'name-cards__constellation--peak' : ''}`}
                  >
                    <span className="name-cards__constellation-root">{root}</span>
                    <span className="name-cards__constellation-count">
                      {count === 0 ? 'absent' : `× ${count}`}
                    </span>
                  </div>
                ))}
              </div>
              <p className="birth-cards__note">
                How often each constellation appears among the letters — the
                gaps matter as much as the peaks.
              </p>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Name Mandala</h3>
              {data.parts.map((part) => (
                <div key={part.input_index} className="name-cards__mandala-part">
                  <div className="name-cards__mandala-label">
                    {part.original}
                    <span className="name-cards__mandala-rhythm">
                      {part.letters.map(letter => letter.is_vowel ? 'V' : 'C').join('')}
                    </span>
                  </div>
                  <div className="name-cards__mandala-row">
                    {part.letters.map((letter, j) => {
                      const major = data.majors_by_number[String(letter.key)];
                      return (
                        <div
                          key={j}
                          className={`name-cards__mandala-tile ${letter.is_vowel ? 'name-cards__mandala-tile--vowel' : ''}`}
                          title={`${letter.letter} = ${major?.name ?? letter.key} · note ${letter.note}`}
                        >
                          {major?.card_id != null ? (
                            <img src={cardThumbnailUrl(major.card_id)} alt={major.name} />
                          ) : (
                            <span className="name-cards__mandala-fallback">{letter.key}</span>
                          )}
                          <span className="name-cards__mandala-letter">
                            {letter.letter}
                            <em>{letter.note}</em>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
              <p className="birth-cards__note">
                Vowels ride above the consonant line. Leading letter:{' '}
                <strong>{data.leading_letter.letter}</strong>
                {' '}({data.leading_letter.is_vowel ? 'vowel' : 'consonant'})
                {data.first_vowel && <> · first vowel: <strong>{data.first_vowel.letter}</strong></>}
                {' '}· laying this out with physical decks would take{' '}
                {data.max_letter_frequency} {data.max_letter_frequency === 1 ? 'deck' : 'decks'}.
              </p>
            </div>

            <p className="birth-cards__footnote">
              Letters follow Mary K. Greer's <em>Archetypal Tarot</em> —
              A through V onto Keys 1–22, W/X/Y/Z reduced. Latin-alphabet
              names only.
            </p>
          </>
        )}
      </div>
    </Modal>
  );
}
