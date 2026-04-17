/** API base URL – override with NEXT_PUBLIC_API_URL env var.
 *  WARNING: Do NOT use plain HTTP in production; it exposes auth tokens.
 *  Always use HTTPS when deploying. */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

if (
  typeof window !== "undefined" &&
  process.env.NODE_ENV === "production" &&
  API_BASE.startsWith("http://")
) {
  console.warn(
    "[research-ui] SECURITY WARNING: NEXT_PUBLIC_API_URL is using plain HTTP in production. " +
    "Set it to an HTTPS URL to protect authentication tokens."
  );
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  skipAuth = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (!skipAuth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, body.detail ?? "Request failed");
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Role = "parent" | "child";

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Mission {
  id: number;
  title: string;
  description: string;
  region: string | null;
  country: string | null;
  program_family: string | null;
  created_by: number;
  created_at: string;
  is_active: number;
}

export type ContributionStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "rejected";

export interface Contribution {
  id: number;
  mission_id: number;
  contributor_id: number;
  camp_name: string;
  website_url: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  venue_name: string | null;
  overnight_confirmed: string | null;
  notes: string | null;
  status: ContributionStatus;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
}

export interface Evidence {
  id: number;
  contribution_id: number;
  url: string | null;
  snippet: string;
  capture_notes: string | null;
  captured_at: string;
}

export interface Answer {
  id: number;
  contribution_id: number;
  question_key: string;
  answer_text: string;
  answered_at: string;
}

export interface GuidedQuestion {
  key: string;
  label: string;
  hint: string;
}

export interface Review {
  id: number;
  contribution_id: number;
  reviewer_id: number;
  action: "approve" | "reject" | "request_changes";
  notes: string | null;
  created_at: string;
}

export interface ExportResult {
  contribution_id: number;
  artifact_path: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Auth endpoints
// ---------------------------------------------------------------------------

export const api = {
  auth: {
    register(username: string, displayName: string, password: string, role: Role): Promise<Token> {
      return request("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, display_name: displayName, password, role }),
      }, true);
    },
    login(username: string, password: string): Promise<Token> {
      const body = new URLSearchParams({ username, password });
      return request("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      }, true);
    },
    me(): Promise<User> {
      return request("/api/auth/me");
    },
  },

  missions: {
    list(): Promise<Mission[]> {
      return request("/api/missions/");
    },
    get(id: number): Promise<Mission> {
      return request(`/api/missions/${id}`);
    },
    create(payload: { title: string; description?: string; region?: string; country?: string; program_family?: string }): Promise<Mission> {
      return request("/api/missions/", { method: "POST", body: JSON.stringify(payload) });
    },
    update(id: number, payload: Partial<Mission>): Promise<Mission> {
      return request(`/api/missions/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    },
    delete(id: number): Promise<void> {
      return request(`/api/missions/${id}`, { method: "DELETE" });
    },
  },

  contributions: {
    list(params?: { mission_id?: number; status?: string }): Promise<Contribution[]> {
      const qs = new URLSearchParams();
      if (params?.mission_id) qs.set("mission_id", String(params.mission_id));
      if (params?.status) qs.set("status", params.status);
      return request(`/api/contributions/?${qs}`);
    },
    get(id: number): Promise<Contribution> {
      return request(`/api/contributions/${id}`);
    },
    create(payload: {
      mission_id: number;
      camp_name: string;
      website_url?: string;
      country?: string;
      region?: string;
      city?: string;
      venue_name?: string;
      overnight_confirmed?: string;
      notes?: string;
    }): Promise<Contribution> {
      return request("/api/contributions/", { method: "POST", body: JSON.stringify(payload) });
    },
    update(id: number, payload: Partial<Contribution>): Promise<Contribution> {
      return request(`/api/contributions/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    },
    submit(id: number): Promise<Contribution> {
      return request(`/api/contributions/${id}/submit`, { method: "POST" });
    },
    delete(id: number): Promise<void> {
      return request(`/api/contributions/${id}`, { method: "DELETE" });
    },
  },

  evidence: {
    list(contributionId: number): Promise<Evidence[]> {
      return request(`/api/contributions/${contributionId}/evidence/`);
    },
    add(contributionId: number, payload: { url?: string; snippet: string; capture_notes?: string }): Promise<Evidence> {
      return request(`/api/contributions/${contributionId}/evidence/`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    delete(contributionId: number, evidenceId: number): Promise<void> {
      return request(`/api/contributions/${contributionId}/evidence/${evidenceId}`, { method: "DELETE" });
    },
  },

  answers: {
    questions(contributionId: number): Promise<GuidedQuestion[]> {
      return request(`/api/contributions/${contributionId}/answers/questions`);
    },
    list(contributionId: number): Promise<Answer[]> {
      return request(`/api/contributions/${contributionId}/answers/`);
    },
    upsert(contributionId: number, answers: { question_key: string; answer_text: string }[]): Promise<Answer[]> {
      return request(`/api/contributions/${contributionId}/answers/`, {
        method: "PUT",
        body: JSON.stringify(answers),
      });
    },
  },

  reviews: {
    queue(): Promise<Contribution[]> {
      return request("/api/reviews/queue");
    },
    post(contributionId: number, action: "approve" | "reject" | "request_changes", notes?: string): Promise<Review> {
      return request(`/api/reviews/${contributionId}`, {
        method: "POST",
        body: JSON.stringify({ action, notes: notes ?? "" }),
      });
    },
    list(contributionId: number): Promise<Review[]> {
      return request(`/api/reviews/${contributionId}`);
    },
  },

  export: {
    preview(contributionId: number): Promise<unknown> {
      return request(`/api/export/preview/${contributionId}`);
    },
    promote(contributionId: number): Promise<ExportResult> {
      return request(`/api/export/${contributionId}`, { method: "POST" });
    },
  },
};
