import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getProfiles } from '../../api/profiles';
import { getDecks } from '../../api/decks';
import { getSpreads } from '../../api/spreads';
import { getEntries } from '../../api/entries';
import { addStarterSpreads, setOnboardingFlags } from '../../api/onboarding';
import type { TabId } from '../layout/TabNav';
import type { Tour } from './tours';
import './GettingStartedPanel.css';

interface GettingStartedPanelProps {
  onGoTo: (tab: TabId) => void;
  onDismissed: () => void;
  onStartTour: (id: Tour['id']) => void;
}

/**
 * The Getting Started checklist: a small floating panel that reads
 * real state (profiles/decks/spreads/entries) and deep-links each
 * step. It retires itself when everything's done, or when dismissed.
 */
export default function GettingStartedPanel({ onGoTo, onDismissed, onStartTour }: GettingStartedPanelProps) {
  const queryClient = useQueryClient();
  const [collapsed, setCollapsed] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const { data: profiles = [] } = useQuery({ queryKey: ['profiles'], queryFn: getProfiles });
  const { data: decks = [] } = useQuery({ queryKey: ['decks'], queryFn: () => getDecks() });
  const { data: spreads = [] } = useQuery({ queryKey: ['spreads'], queryFn: getSpreads });
  const { data: entries = [] } = useQuery({ queryKey: ['entries'], queryFn: () => getEntries() });

  const items = [
    {
      label: 'Create your profile',
      done: profiles.length > 0,
      tab: 'profiles' as TabId,
    },
    {
      label: 'Import your first deck',
      done: decks.length > 0,
      tab: 'library' as TabId,
      tour: 'deck' as Tour['id'],
    },
    {
      label: 'Add a spread',
      done: spreads.length > 0,
      tab: 'spreads' as TabId,
      starter: true,
      tour: 'spread' as Tour['id'],
    },
    {
      label: 'Record your first reading',
      done: entries.length > 0,
      tab: 'journal' as TabId,
      tour: 'entry' as Tour['id'],
    },
  ];

  const doneCount = items.filter((i) => i.done).length;
  if (doneCount === items.length) return null;

  const handleStarterSpreads = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setSeeding(true);
    try {
      await addStarterSpreads();
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
    } finally {
      setSeeding(false);
    }
  };

  const dismiss = async () => {
    try {
      await setOnboardingFlags({ checklist_dismissed: true });
    } catch { /* worst case it reappears next launch */ }
    onDismissed();
  };

  return (
    <div className="getting-started">
      <div
        className="getting-started__header"
        role="button"
        tabIndex={0}
        onClick={() => setCollapsed(!collapsed)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') setCollapsed(!collapsed);
        }}
      >
        <span className="getting-started__title">
          Getting started · {doneCount} of {items.length}
        </span>
        <span className="getting-started__chevron">{collapsed ? '▸' : '▾'}</span>
        <button
          className="getting-started__close"
          title="Dismiss for good — everything stays reachable from its own tab"
          onClick={(e) => { e.stopPropagation(); dismiss(); }}
        >
          ×
        </button>
      </div>

      {!collapsed && (
        <ul className="getting-started__list">
          {items.map((item) => (
            <li key={item.label}>
              <button
                className={`getting-started__item ${item.done ? 'getting-started__item--done' : ''}`}
                onClick={() => {
                  onGoTo(item.tab);
                  if ('tour' in item && item.tour) onStartTour(item.tour);
                }}
                disabled={item.done}
              >
                <span className="getting-started__mark">
                  {item.done ? '✓' : '○'}
                </span>
                {item.label}
              </button>
              {item.starter && !item.done && (
                <button
                  className="getting-started__starter"
                  onClick={handleStarterSpreads}
                  disabled={seeding}
                >
                  {seeding ? 'Adding…' : 'Add 5 classics'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
