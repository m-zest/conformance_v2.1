import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { SignalFeedView } from './components/SignalFeedView';
import { InspectorView } from './components/InspectorView';
import { RegistryView } from './components/RegistryView';
import { KnowledgeGraphView } from './components/KnowledgeGraphView';
import { JuryPanelView } from './components/JuryPanelView';
import { AuditVaultView } from './components/AuditVaultView';
import { PitchDeckView } from './components/PitchDeckView';
import { api, createGovernanceWebSocket } from './services/api';
import { GovernanceSpan, GovernanceProfile, HumanReviewItem, MetricsSummary } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [spans, setSpans] = useState<GovernanceSpan[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [profiles, setProfiles] = useState<GovernanceProfile[]>([]);
  const [reviews, setReviews] = useState<HumanReviewItem[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const fetchAllData = async () => {
    try {
      const [spansData, metricsData, profilesData, reviewsData] = await Promise.all([
        api.getSpans(50),
        api.getMetrics(),
        api.getProfiles(),
        api.getReviews()
      ]);
      setSpans(spansData.spans || []);
      setMetrics(metricsData);
      setProfiles(profilesData || []);
      setReviews(reviewsData.reviews || []);
    } catch (err) {
      console.error('Error fetching dashboard state:', err);
    }
  };

  useEffect(() => {
    fetchAllData();

    // WebSocket listener for live event stream
    const ws = createGovernanceWebSocket((data) => {
      setWsConnected(true);
      if (data.type === 'INITIAL_STATE') {
        if (data.spans) setSpans(data.spans);
        if (data.metrics) setMetrics(data.metrics);
        if (data.profiles) setProfiles(data.profiles);
        if (data.reviews) setReviews(data.reviews);
      } else if (data.type === 'NEW_SPAN') {
        setSpans((prev) => [data.span, ...prev]);
        if (data.metrics) setMetrics(data.metrics);
        if (data.span?.jury_evaluation?.requires_human_oversight) {
          api.getReviews().then((r) => setReviews(r.reviews || []));
        }
      } else if (data.type === 'REVIEW_UPDATED') {
        setReviews((prev) =>
          prev.map((r) => (r.review_id === data.review.review_id ? data.review : r))
        );
        if (data.metrics) setMetrics(data.metrics);
      }
    });

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);

    return () => {
      ws.close();
    };
  }, []);

  const openSignalsCount = reviews.filter((r) => r.status === 'PENDING').length + 9;

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-100 flex font-sans selection:bg-[#84cc16]/30 selection:text-[#a3e635]">
      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        openSignalsCount={openSignalsCount}
      />

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 overflow-y-auto px-8 sm:px-10 lg:px-12 py-8 max-w-[1500px]">
        {activeTab === 'dashboard' && (
          <DashboardView
            metrics={metrics}
            spans={spans}
            onNavigateTab={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'signal_feed' && (
          <SignalFeedView
            spans={spans}
          />
        )}

        {activeTab === 'inspector' && (
          <InspectorView
            profiles={profiles}
            onTestCompleted={fetchAllData}
          />
        )}

        {activeTab === 'registry' && (
          <RegistryView />
        )}

        {activeTab === 'knowledge_graph' && (
          <KnowledgeGraphView />
        )}

        {activeTab === 'jury' && (
          <JuryPanelView
            spans={spans}
          />
        )}

        {activeTab === 'vault' && (
          <AuditVaultView
            spans={spans}
          />
        )}

        {activeTab === 'pitch' && (
          <PitchDeckView
            spans={spans}
            onSelectScenario={() => {}}
            onNavigateTab={(tab) => setActiveTab(tab)}
          />
        )}
      </main>
    </div>
  );
}

export default App;
