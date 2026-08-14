import { GovernanceSpan, GovernanceProfile, HumanReviewItem, MetricsSummary } from '../types';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000/ws';

export const api = {
  async getMetrics(): Promise<MetricsSummary> {
    const res = await fetch(`${API_BASE}/api/metrics`);
    return res.json();
  },

  async getSpans(limit = 50, offset = 0): Promise<{ spans: GovernanceSpan[]; total: number }> {
    const res = await fetch(`${API_BASE}/api/spans?limit=${limit}&offset=${offset}`);
    return res.json();
  },

  async getSpan(spanId: string): Promise<GovernanceSpan> {
    const res = await fetch(`${API_BASE}/api/spans/${spanId}`);
    return res.json();
  },

  async getProfiles(): Promise<GovernanceProfile[]> {
    const res = await fetch(`${API_BASE}/api/profiles`);
    return res.json();
  },

  async updateProfile(profile: GovernanceProfile): Promise<{ status: string; profile: GovernanceProfile }> {
    const res = await fetch(`${API_BASE}/api/profiles/${profile.profile_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    });
    return res.json();
  },

  async getReviews(): Promise<{ reviews: HumanReviewItem[] }> {
    const res = await fetch(`${API_BASE}/api/reviews`);
    return res.json();
  },

  async arbitrateReview(reviewId: string, decision: string, officer: string, notes: string): Promise<HumanReviewItem> {
    const res = await fetch(`${API_BASE}/api/reviews/${reviewId}/arbitrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, officer, notes })
    });
    return res.json();
  },

  async testEvaluate(prompt: string, profileId: string, mode: string, model: string): Promise<any> {
    const res = await fetch(`${API_BASE}/govern/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        profile_id: profileId,
        mode,
        model,
        client_type: 'PLAYGROUND_SANDBOX',
        app_name: 'Governance-Sandbox'
      })
    });
    return res.json();
  },

  async triggerScenario(scenarioId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/scenarios/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId })
    });
    return res.json();
  },

  async verifyVault(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/vault/verify`);
    return res.json();
  },

  async exportCompliancePack(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/vault/export`);
    return res.json();
  }
};

export function createGovernanceWebSocket(onMessage: (data: any) => void): WebSocket {
  let ws: WebSocket;
  const connect = () => {
    ws = new WebSocket(WS_BASE);
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onMessage(parsed);
      } catch (err) {
        console.error('WS Parse error', err);
      }
    };
    ws.onclose = () => {
      // Reconnect after 2 seconds
      setTimeout(connect, 2000);
    };
  };
  connect();
  return ws!;
}
