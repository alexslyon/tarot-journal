import { useState, useEffect } from 'react';
import GeneralSection from './sections/GeneralSection';
import ProfilesSection from './sections/ProfilesSection';
import TagsSection from './sections/TagsSection';
import ImportPresetsSection from './sections/ImportPresetsSection';
import BackupSection from './sections/BackupSection';
import CacheSection from './sections/CacheSection';
import CorrespondencesSection from './sections/CorrespondencesSection';
import LenormandCombinationsSection from './sections/LenormandCombinationsSection';
import './SettingsLayout.css';

export type SettingsSectionId =
  | 'general'
  | 'profiles'
  | 'tags'
  | 'correspondences'
  | 'lenormand-combinations'
  | 'import-presets'
  | 'backup'
  | 'cache';

const SECTIONS: { id: SettingsSectionId; label: string }[] = [
  { id: 'general', label: 'General' },
  { id: 'profiles', label: 'Profiles' },
  { id: 'tags', label: 'Tags' },
  { id: 'correspondences', label: 'Correspondences' },
  { id: 'lenormand-combinations', label: 'Lenormand Combinations' },
  { id: 'import-presets', label: 'Import Presets' },
  { id: 'backup', label: 'Backup & Restore' },
  { id: 'cache', label: 'Thumbnail Cache' },
];

interface SettingsLayoutProps {
  initialSection?: string;
  /** Optional pre-selected card pair for the Lenormand Combinations editor
   *  (used by the Reference deep-link). */
  initialLenormandCombination?: { card_1: number; card_2: number };
  onSectionViewed?: () => void;
}

export default function SettingsLayout({
  initialSection,
  initialLenormandCombination,
  onSectionViewed,
}: SettingsLayoutProps) {
  const [activeSection, setActiveSection] = useState<SettingsSectionId>('general');

  useEffect(() => {
    if (initialSection && SECTIONS.some(s => s.id === initialSection)) {
      setActiveSection(initialSection as SettingsSectionId);
      onSectionViewed?.();
    }
  }, [initialSection, onSectionViewed]);

  return (
    <div className="settings-layout">
      <nav className="settings-layout__sidebar">
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            className={`settings-layout__nav-item ${activeSection === section.id ? 'settings-layout__nav-item--active' : ''}`}
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
          </button>
        ))}
      </nav>
      <div className="settings-layout__content">
        {activeSection === 'general' && <GeneralSection />}
        {activeSection === 'profiles' && <ProfilesSection />}
        {activeSection === 'tags' && <TagsSection />}
        {activeSection === 'correspondences' && <CorrespondencesSection />}
        {activeSection === 'lenormand-combinations' && (
          <LenormandCombinationsSection
            initialCards={initialLenormandCombination}
          />
        )}
        {activeSection === 'import-presets' && <ImportPresetsSection />}
        {activeSection === 'backup' && <BackupSection />}
        {activeSection === 'cache' && <CacheSection />}
      </div>
    </div>
  );
}
