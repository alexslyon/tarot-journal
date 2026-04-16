import { useState } from 'react';
import CorrespondencesViewer from './sections/CorrespondencesViewer';
import LenormandSection from './sections/LenormandSection';
import CardNamesSection from './sections/CardNamesSection';
import NumerologySection from './sections/NumerologySection';
import './ReferenceTab.css';

type ReferenceSectionId = 'correspondences' | 'lenormand' | 'card-names' | 'numerology';

const SECTIONS: { id: ReferenceSectionId; label: string }[] = [
  { id: 'correspondences', label: 'Correspondences' },
  { id: 'lenormand', label: 'Lenormand' },
  { id: 'card-names', label: 'Card Names' },
  { id: 'numerology', label: 'Numerology' },
];

interface ReferenceTabProps {
  onNavigateToSettings?: (section: string) => void;
}

export default function ReferenceTab({ onNavigateToSettings }: ReferenceTabProps) {
  const [activeSection, setActiveSection] = useState<ReferenceSectionId>('correspondences');

  return (
    <div className="reference-layout">
      <nav className="reference-layout__sidebar">
        {SECTIONS.map((section) => (
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
          <CorrespondencesViewer onEditCorrespondences={onNavigateToSettings} />
        )}
        {activeSection === 'lenormand' && <LenormandSection />}
        {activeSection === 'card-names' && <CardNamesSection />}
        {activeSection === 'numerology' && <NumerologySection />}
      </div>
    </div>
  );
}
