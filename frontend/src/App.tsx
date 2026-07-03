import { useState, useCallback, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmDialogHost } from './components/common/ConfirmDialog';
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
  combination?: {
    cartomancy_type: string;
    archetype_1_id: number;
    archetype_2_id: number;
  };
  archetypeId?: number;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('library');
  const [settingsSection, setSettingsSection] = useState<string | undefined>();
  const [settingsPayload, setSettingsPayload] = useState<SettingsDeepLinkPayload | undefined>();
  const [pendingNewEntry, setPendingNewEntry] = useState(false);

  // Cmd+N (Ctrl+N elsewhere) starts a new journal entry from any tab —
  // the app's single most common action. Ignored while any dialog is
  // open so it can't stack a second editor on top of one in progress.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'n' && (e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey) {
        if (document.querySelector('.modal-overlay, .confirm-dialog__overlay')) return;
        e.preventDefault();
        setActiveTab('journal');
        setPendingNewEntry(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const handleNewEntryHandled = useCallback(() => setPendingNewEntry(false), []);

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
              {activeTab === 'journal' && (
                <JournalTab
                  pendingNewEntry={pendingNewEntry}
                  onNewEntryHandled={handleNewEntryHandled}
                />
              )}
              {activeTab === 'reference' && (
                <ReferenceTab onNavigateToSettings={handleNavigateToSettings} />
              )}
              {activeTab === 'insights' && <StatsTab />}
              {activeTab === 'settings' && (
                <SettingsTab
                  initialSection={settingsSection}
                  initialCombination={settingsPayload?.combination}
                  initialArchetypeId={settingsPayload?.archetypeId}
                  onSectionViewed={handleSettingsSectionViewed}
                />
              )}
            </div>
          </div>
          <ConfirmDialogHost />
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
