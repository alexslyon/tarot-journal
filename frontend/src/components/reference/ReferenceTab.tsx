import { useEffect, useState } from 'react';
import CorrespondencesViewer from './sections/CorrespondencesViewer';
import CombinationsViewer from './sections/CombinationsViewer';
import ArchetypesViewer from './sections/ArchetypesViewer';
import './ReferenceTab.css';

type ReferenceSectionId =
  | 'archetypes'
  | 'correspondences'
  | 'combinations';

const SECTIONS: { id: ReferenceSectionId; label: string }[] = [
  { id: 'archetypes', label: 'Archetypes' },
  { id: 'correspondences', label: 'Correspondences' },
  { id: 'combinations', label: 'Combinations' },
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
      };
      archetypeId?: number;
      fieldId?: number;
    },
  ) => void;
  /** External request to open a specific reference section (deep link). */
  initialSection?: ReferenceSectionId;
  onSectionViewed?: () => void;
}

export default function ReferenceTab({
  onNavigateToSettings,
  initialSection,
  onSectionViewed,
}: ReferenceTabProps) {
  const [activeSection, setActiveSection] = useState<ReferenceSectionId>('archetypes');

  useEffect(() => {
    if (initialSection && SECTIONS.some(s => s.id === initialSection)) {
      setActiveSection(initialSection);
      onSectionViewed?.();
    }
  }, [initialSection, onSectionViewed]);

  return (
    <div className="reference-layout">
      <nav className="reference-layout__sidebar">
        {SECTIONS.map(section => (
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
          <CombinationsViewer
            onEditCombination={
              onNavigateToSettings
                ? (cartomancy_type, archetype_1_id, archetype_2_id) =>
                    onNavigateToSettings('combinations', {
                      combination: { cartomancy_type, archetype_1_id, archetype_2_id },
                    })
                : undefined
            }
          />
        )}
      </div>
    </div>
  );
}
