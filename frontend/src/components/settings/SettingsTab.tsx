import SettingsLayout from './SettingsLayout';

interface SettingsTabProps {
  initialSection?: string;
  initialLenormandCombination?: { card_1: number; card_2: number };
  onSectionViewed?: () => void;
}

export default function SettingsTab({
  initialSection,
  initialLenormandCombination,
  onSectionViewed,
}: SettingsTabProps) {
  return (
    <SettingsLayout
      initialSection={initialSection}
      initialLenormandCombination={initialLenormandCombination}
      onSectionViewed={onSectionViewed}
    />
  );
}
