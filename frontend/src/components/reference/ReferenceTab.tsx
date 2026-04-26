import { useEffect, useState } from 'react';
import CorrespondencesViewer from './sections/CorrespondencesViewer';
import LenormandCombinationsViewer from './sections/LenormandCombinationsViewer';
import './ReferenceTab.css';

type ReferenceSectionId = 'correspondences' | 'lenormand-combinations';

const SECTIONS: { id: ReferenceSectionId; label: string }[] = [
  { id: 'correspondences', label: 'Correspondences' },
  { id: 'lenormand-combinations', label: 'Lenormand Combinations' },
];

interface ReferenceTabProps {
  /** Navigate to Settings — first arg is the section id, second is optional payload. */
  onNavigateToSettings?: (
    section: string,
    payload?: { lenormandCombination?: { card_1: number; card_2: number } },
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
  const [activeSection, setActiveSection] = useState<ReferenceSectionId>('correspondences');

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
        {activeSection === 'correspondences' && (
          <CorrespondencesViewer
            onEditCorrespondences={
              onNavigateToSettings
                ? (section: string) => onNavigateToSettings(section)
                : undefined
            }
          />
        )}
        {activeSection === 'lenormand-combinations' && (
          <LenormandCombinationsViewer
            onEditCombination={
              onNavigateToSettings
                ? (card_1, card_2) =>
                    onNavigateToSettings('lenormand-combinations', {
                      lenormandCombination: { card_1, card_2 },
                    })
                : undefined
            }
          />
        )}
      </div>
    </div>
  );
}
