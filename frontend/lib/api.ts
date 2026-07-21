import type {
  Application,
  BD,
  Client,
  ComparisonRun,
  Job,
  JobSource,
  KeywordAnalysis,
  LocationAnalysis,
  Profile,
  ProfilePerformance,
  ResumeExtraction,
  ScrapeRun,
  TargetRole,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const TOKEN_KEY = "applytics_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (data?.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // response wasn't JSON; keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") usp.set(key, String(value));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  auth: {
    register: (email: string, password: string, full_name: string) =>
      request<BD>("/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
    login: (email: string, password: string) =>
      request<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
  },

  bds: {
    me: () => request<BD>("/bds/me"),
  },

  clients: {
    list: () => request<Client[]>("/clients"),
    create: (payload: {
      full_name: string;
      email: string;
      current_city?: string;
      current_state?: string;
      current_country?: string;
      timezone?: string;
    }) => request<Client>("/clients", { method: "POST", body: JSON.stringify(payload) }),
    get: (id: string) => request<Client>(`/clients/${id}`),
    extractResume: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<ResumeExtraction>("/clients/extract-resume", { method: "POST", body: formData });
    },
    extractLinkedinText: (text: string) =>
      request<ResumeExtraction>("/clients/extract-linkedin-text", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    extractLinkedinUrl: (url: string) =>
      request<ResumeExtraction>("/clients/extract-linkedin-url", {
        method: "POST",
        body: JSON.stringify({ url }),
      }),
    listTargetRoles: (id: string) => request<TargetRole[]>(`/clients/${id}/target-roles`),
    createTargetRole: (id: string, payload: { title: string; seniority?: string; must_have_keywords: string[] }) =>
      request<TargetRole>(`/clients/${id}/target-roles`, { method: "POST", body: JSON.stringify(payload) }),
    performance: (id: string, targetRoleId?: string) =>
      request<ProfilePerformance[]>(`/clients/${id}/performance${qs({ target_role_id: targetRoleId })}`),
  },

  profiles: {
    create: (payload: {
      client_id: string;
      target_role_id?: string | null;
      type: string;
      variant_label: string;
      source_url?: string;
      raw_text?: string;
    }) => request<Profile>("/profiles", { method: "POST", body: JSON.stringify(payload) }),
    upload: (formData: FormData) => request<Profile>("/profiles/upload", { method: "POST", body: formData }),
    list: (clientId: string) => request<Profile[]>(`/profiles${qs({ client_id: clientId })}`),
  },

  scrape: {
    sources: () => request<JobSource[]>("/scrape/sources"),
    trigger: (payload: {
      source: string;
      keywords?: string;
      remote_only?: boolean;
      country?: string;
      max_results?: number;
    }) => request<ScrapeRun>("/scrape/runs", { method: "POST", body: JSON.stringify(payload) }),
  },

  jobs: {
    list: (filters: { remote_type?: string; country?: string; source?: string; keyword?: string; limit?: number }) =>
      request<Job[]>(`/jobs${qs(filters)}`),
  },

  analysis: {
    keywords: (profile_id: string, target_role_id?: string | null) =>
      request<KeywordAnalysis>("/analysis/keywords", {
        method: "POST",
        body: JSON.stringify({ profile_id, target_role_id }),
      }),
    location: (client_id: string, target_role_id?: string | null) =>
      request<LocationAnalysis>("/analysis/location", {
        method: "POST",
        body: JSON.stringify({ client_id, target_role_id }),
      }),
    compare: (client_id: string, profile_ids: string[], target_role_id?: string | null) =>
      request<ComparisonRun>("/analysis/compare", {
        method: "POST",
        body: JSON.stringify({ client_id, profile_ids, target_role_id }),
      }),
  },

  applications: {
    create: (payload: { client_id: string; profile_id: string; job_id: string; notes?: string }) =>
      request<Application>("/applications", { method: "POST", body: JSON.stringify(payload) }),
    list: (clientId: string) => request<Application[]>(`/applications${qs({ client_id: clientId })}`),
    update: (id: string, payload: { status?: string; notes?: string }) =>
      request<Application>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  },
};
