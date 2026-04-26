import { useState, useCallback } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import TabNav, { type TabId } from './components/layout/TabNav';
import LibraryTab from './components/library/LibraryTab';
import JournalTab from './components/journal/JournalTab';
import SpreadsTab from './components/spreads/SpreadsTab';
import ReferenceTab from './components/reference/ReferenceTab';
import StatsTab from './components/stats/StatsTab';
import SettingsTab from './components/settings/SettingsTab';
import './styles/globals.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

interface SettingsDeepLinkPayload {
  lenormandCombination?: { card_1: number; card_2: number };
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('library');
  const [settingsSection, setSettingsSection] = useState<string | undefined>();
  const [settingsPayload, setSettingsPayload] = useState<SettingsDeepLinkPayload | undefined>();

  const handleTabChange = useCallback((tab: TabId, section?: string) => {
    setActiveTab(tab);
    if (tab === 'settings' && section) {
      setSettingsSection(section);
    }
  }, []);

  const handleSettingsSectionViewed = useCallback(() => {
    setSettingsSection(undefined);
    setSettingsPayload(undefined);
  }, []);

  const handleNavigateToSettings = useCallback(
    (section: string, payload?: SettingsDeepLinkPayload) => {
      setSettingsPayload(payload);
      handleTabChange('settings', section);
    },
    [handleTabChange],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            <TabNav activeTab={activeTab} onTabChange={handleTabChange} />
            <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
              {activeTab === 'library' && <LibraryTab />}
              {activeTab === 'spreads' && <SpreadsTab />}
              {activeTab === 'journal' && <JournalTab />}
              {activeTab === 'reference' && (
                <ReferenceTab onNavigateToSettings={handleNavigateToSettings} />
              )}
              {activeTab === 'insights' && <StatsTab />}
              {activeTab === 'settings' && (
                <SettingsTab
                  initialSection={settingsSection}
                  initialLenormandCombination={settingsPayload?.lenormandCombination}
                  onSectionViewed={handleSettingsSectionViewed}
                />
              )}
            </div>
          </div>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
