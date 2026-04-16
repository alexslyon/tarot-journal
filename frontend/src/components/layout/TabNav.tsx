import './TabNav.css';

export type TabId = 'library' | 'spreads' | 'journal' | 'reference' | 'insights' | 'settings';

interface TabNavProps {
  activeTab: TabId;
  onTabChange: (tab: TabId, section?: string) => void;
}

const TABS: { id: TabId; label: string; isIcon?: boolean }[] = [
  { id: 'library', label: 'Library' },
  { id: 'spreads', label: 'Spreads' },
  { id: 'journal', label: 'Journal' },
  { id: 'reference', label: 'Reference' },
  { id: 'insights', label: 'Insights' },
  { id: 'settings', label: '\u2699', isIcon: true },
];

export default function TabNav({ activeTab, onTabChange }: TabNavProps) {
  return (
    <nav className="tab-nav">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tab-nav__tab ${activeTab === tab.id ? 'tab-nav__tab--active' : ''} ${tab.isIcon ? 'tab-nav__tab--icon' : ''}`}
          onClick={() => onTabChange(tab.id)}
          title={tab.isIcon ? 'Settings' : undefined}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
