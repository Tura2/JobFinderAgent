const BASE_URL = import.meta.env.VITE_API_URL || "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }

  if (!resp.ok) {
    throw new Error(`API error ${resp.status}: ${await resp.text()}`);
  }

  return resp.json();
}

export const api = {
  getMatches: () => apiFetch<import("../types").MatchListItem[]>("/matches"),
  getMatch: (id: number) => apiFetch<import("../types").MatchDetail>(`/matches/${id}`),
  skipMatch: (id: number) => apiFetch<{ status: string }>(`/matches/${id}/skip`, { method: "POST" }),
  applyMatch: (id: number, atsUrl?: string, chosenCvVariantId?: number) =>
    apiFetch<{ match: import("../types").MatchListItem; application: { id: number }; ats_url: string }>(
      `/matches/${id}/applied`,
      { method: "POST", body: JSON.stringify({ ats_url: atsUrl, chosen_cv_variant_id: chosenCvVariantId }) }
    ),
  getNearMisses: (minScore = 30) =>
    apiFetch<import("../types").MatchListItem[]>(`/matches/near-misses?min_score=${minScore}`),
  promoteMatch: (id: number) =>
    apiFetch<{ id: number; status: string }>(`/matches/${id}/promote`, { method: "POST" }),

  getTracker: () => apiFetch<import("../types").Application[]>("/tracker"),
  updateApplication: (id: number, data: { outcome_status?: string; notes?: string }) =>
    apiFetch<import("../types").Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getCompanies: () => apiFetch<import("../types").Company[]>("/companies"),
  addCompany: (data: Partial<import("../types").Company>) =>
    apiFetch<import("../types").Company>("/companies", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCompany: (id: number, data: Partial<import("../types").Company>) =>
    apiFetch<import("../types").Company>(`/companies/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteCompany: (id: number) =>
    apiFetch<{ deleted: boolean }>(`/companies/${id}`, { method: "DELETE" }),

  getCVVariants: () => apiFetch<import("../types").CVVariant[]>("/cv-variants"),
  addCVVariant: (data: { name: string; file_path: string; focus_tags: string }) =>
    apiFetch<import("../types").CVVariant>("/cv-variants", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  triggerScan: () => apiFetch<{ message: string }>("/trigger-scan", { method: "POST" }),
  getScanStatus: () => apiFetch<import("../types").ScanStatus>("/scan-status"),

  getConfig: () => apiFetch<{ linkedin_url: string }>("/config"),
};
