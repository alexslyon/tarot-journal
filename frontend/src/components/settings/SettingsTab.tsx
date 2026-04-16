import SettingsLayout from './SettingsLayout';

interface SettingsTabProps {
  initialSection?: string;
  onSectionViewed?: () => void;
}

export default function SettingsTab({ initialSection, onSectionViewed }: SettingsTabProps) {
  return <SettingsLayout initialSection={initialSection} onSectionViewed={onSectionViewed} />;
}
