import { useEffect, useState } from 'react';
import CorrespondencesViewer from './sections/CorrespondencesViewer';
import CombinationsViewer from './sections/CombinationsViewer';
import ArchetypesViewer from './sections/ArchetypesViewer';
import AstrologySection from './sections/AstrologySection';
import KabbalahSection from './sections/KabbalahSection';
import NumerologySection from './sections/NumerologySection';
import ChakrasSection from './sections/ChakrasSection';
import './ReferenceTab.css';

export type ReferenceSectionId =
  | 'archetypes'
  | 'correspondences'
  | 'combinations'
  | 'astrology'
  | 'kabbalah'
  | 'numerology'
  | 'chakras';

export const REFERENCE_SECTIONS: { id: ReferenceSectionId; label: string }[] = [
  { id: 'archetypes', label: 'Archetypes' },
  { id: 'correspondences', label: 'Correspondences' },
  { id: 'combinations', label: 'Combinations' },
  { id: 'astrology', label: 'Astrology' },
  { id: 'kabbalah', label: 'Kabbalah' },
  { id: 'numerology', label: 'Numerology' },
  { id: 'chakras', label: 'Chakras' },
];

interface ReferenceTabProps {
  /** Navigate to Settings — first arg is the section id, second is optional payload. */
  onNavigateToSettings?: (
    section: string,
    payload?: {
      combination?: {
        cartomancy_type: string;
        archetype_1_id: number;
        archetype_2_id: number;
        archetype_1_reversed?: boolean;
        archetype_2_reversed?: boolean;
      };
      archetypeId?: number;
      fieldId?: number;
    },
  ) => void;
  /** External request to open a specific reference section (deep link). */
  initialSection?: ReferenceSectionId;
  onSectionViewed?: () => void;
  /** Archetype to select on arrival (set by the command palette). */
  pendingArchetype?: { id: number; cartomancyType: string } | null;
  onPendingArchetypeHandled?: () => void;
}

export default function ReferenceTab({
  onNavigateToSettings,
  initialSection,
  onSectionViewed,
  pendingArchetype,
  onPendingArchetypeHandled,
}: ReferenceTabProps) {
  const [activeSection, setActiveSection] = useState<ReferenceSectionId>('archetypes');
  // "In your correspondences" chips in the content sections jump to
  // the Archetypes viewer — same mechanism as the palette's deep link,
  // but originating inside this tab.
  const [localArchetype, setLocalArchetype] =
    useState<{ id: number; cartomancyType: string } | null>(null);

  // A pending archetype always lands on the Archetypes section.
  useEffect(() => {
    if (pendingArchetype) setActiveSection('archetypes');
  }, [pendingArchetype]);

  useEffect(() => {
    if (initialSection && REFERENCE_SECTIONS.some(s => s.id === initialSection)) {
      setActiveSection(initialSection);
      onSectionViewed?.();
    }
  }, [initialSection, onSectionViewed]);

  const openArchetype = (id: number, cartomancyType: string) => {
    setLocalArchetype({ id, cartomancyType });
    setActiveSection('archetypes');
  };

  return (
    <div className="reference-layout">
      <nav className="reference-layout__sidebar">
        {REFERENCE_SECTIONS.map(section => (
          <button
            key={section.id}
            className={`reference-layout__nav-item ${activeSection === section.id ? 'reference-layout__nav-item--active' : ''}`}
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
          </button>
        ))}
      </nav>
      <div className="reference-layout__content">
        {activeSection === 'archetypes' && (
          <ArchetypesViewer
            pendingArchetype={pendingArchetype ?? localArchetype}
            onPendingArchetypeHandled={() => {
              setLocalArchetype(null);
              onPendingArchetypeHandled?.();
            }}
            onNavigateToSettings={
              onNavigateToSettings
                ? (section, payload) => onNavigateToSettings(section, payload)
                : undefined
            }
          />
        )}
        {activeSection === 'correspondences' && (
          <CorrespondencesViewer
            onEditCorrespondences={
              onNavigateToSettings
                ? (section: string) => onNavigateToSettings(section)
                : undefined
            }
          />
        )}
        {activeSection === 'combinations' && (
          <CombinationsViewer />
        )}
        {activeSection === 'astrology' && (
          <AstrologySection onOpenArchetype={openArchetype} />
        )}
        {activeSection === 'kabbalah' && (
          <KabbalahSection />
        )}
        {activeSection === 'numerology' && (
          <NumerologySection onOpenArchetype={openArchetype} />
        )}
        {activeSection === 'chakras' && (
          <ChakrasSection onOpenArchetype={openArchetype} />
        )}
      </div>
    </div>
  );
}
