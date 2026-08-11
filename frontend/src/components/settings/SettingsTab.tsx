import SettingsLayout from './SettingsLayout';

interface SettingsTabProps {
  initialSection?: string;
  initialCombination?: {
    cartomancy_type: string;
    archetype_1_id: number;
    archetype_2_id: number;
    archetype_1_reversed?: boolean;
    archetype_2_reversed?: boolean;
  };
  initialArchetypeId?: number;
  onSectionViewed?: () => void;
}

export default function SettingsTab({
  initialSection,
  initialCombination,
  initialArchetypeId,
  onSectionViewed,
}: SettingsTabProps) {
  return (
    <SettingsLayout
      initialSection={initialSection}
      initialCombination={initialCombination}
      initialArchetypeId={initialArchetypeId}
      onSectionViewed={onSectionViewed}
    />
  );
}
