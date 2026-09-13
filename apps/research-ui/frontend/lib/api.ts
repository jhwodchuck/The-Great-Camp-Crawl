/** API base URL – browser calls the backend directly; SSR uses the same env var.
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

export interface RegisterOptions {
  child_self_signup_enabled: boolean;
  parent_self_signup_enabled: boolean;
  parent_invite_required: boolean;
  bootstrap_parent_configured: boolean;
  message: string | null;
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
  storage_kind: string;
  exported_at: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Camp Catalog types
// ---------------------------------------------------------------------------

export interface Camp {
  id: number;
  record_id: string;
  name: string;
  display_name: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  venue_name: string | null;
  program_family: string | null;
  camp_types: string | null;
  website_url: string | null;
  ages_min: number | null;
  ages_max: number | null;
  grades_min: number | null;
  grades_max: number | null;
  duration_min_days: number | null;
  duration_max_days: number | null;
  pricing_currency: string | null;
  pricing_min: number | null;
  pricing_max: number | null;
  boarding_included: boolean | null;
  overnight_confirmed: boolean | null;
  active_confirmed: boolean | null;
  confidence: string | null;
  operator_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  draft_status: string | null;
  is_excluded: boolean | null;
  exclusion_reason: string | null;
  exclusion_notes: string | null;
  excluded_at: string | null;
  excluded_by_user_id: number | null;
  description_md: string | null;
  last_verified: string | null;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface CampListResponse {
  items: Camp[];
  total: number;
  page: number;
  page_size: number;
}

export interface CampStats {
  total: number;
  by_country: Record<string, number>;
  by_region: Record<string, number>;
  regions_by_country: Record<string, Record<string, number>>;
  by_program_family: Record<string, number>;
}

export interface CampModerationPayload {
  is_excluded: boolean;
  reason?: string;
  notes?: string;
}

export interface CampEnrichmentPayload {
  ages_min?: number | null;
  ages_max?: number | null;
  grades_min?: number | null;
  grades_max?: number | null;
  duration_min_days?: number | null;
  duration_max_days?: number | null;
  pricing_currency?: string | null;
  pricing_min?: number | null;
  pricing_max?: number | null;
  boarding_included?: boolean | null;
  overnight_confirmed?: boolean | null;
  active_confirmed?: boolean | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  operator_name?: string | null;
  description_md?: string | null;
  confidence?: string | null;
  draft_status?: string | null;
  city?: string | null;
  region?: string | null;
}

export interface Favorite {
  id: number;
  user_id: number;
  camp_id: number;
  notes: string | null;
  created_at: string;
  camp: Camp;
}

export interface ScrapeResult {
  url: string;
  title: string | null;
  description: string | null;
  pricing: { currency?: string; min?: number; max?: number } | null;
  ages: { min?: number; max?: number; grade_min?: number; grade_max?: number } | null;
  duration: { min_days?: number; max_days?: number } | null;
  contact: { email?: string; phone?: string } | null;
  overnight_signals: string[];
  evidence_snippets: string[];
}

// ---------------------------------------------------------------------------
// Summer Plans (v2)
// ---------------------------------------------------------------------------

export interface CampPlanMembership {
  plan_id: number;
  plan_title: string;
  plan_year: number;
  shortlist_item_id: number;
  status: string;
}

export interface SummerPlan {
  id: number;
  title: string;
  description: string;
  year: number;
  target_age: number | null;
  target_grade: number | null;
  created_at: string;
  is_active: number;
}

export type ShortlistStatus = "interested" | "researching" | "applied" | "going" | "passed";

export interface ShortlistNote {
  id: number;
  shortlist_item_id: number;
  author_id: number;
  author_display_name: string | null;
  body: string;
  source_url: string | null;
  created_at: string;
}

export interface ShortlistItem {
  id: number;
  plan_id: number;
  camp_id: number | null;
  custom_camp_name: string | null;
  custom_camp_url: string | null;
  status: ShortlistStatus;
  added_by: number;
  created_at: string;
  updated_at: string;
  camp: Camp | null;
  notes: ShortlistNote[];
}

export interface ResearchClipboard {
  plan_title: string;
  items: Record<string, unknown>[];
}

// ---------------------------------------------------------------------------
// Auth endpoints
// ---------------------------------------------------------------------------

export const api = {
  auth: {
    register(
      username: string,
      displayName: string,
      password: string,
      role: Role,
      parentInviteCode?: string
    ): Promise<Token> {
      return request("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username,
          display_name: displayName,
          password,
          role,
          parent_invite_code: parentInviteCode || undefined,
        }),
      }, true);
    },
    registerOptions(): Promise<RegisterOptions> {
      return request("/api/auth/register-options", {}, true);
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

  camps: {
    list(params?: {
      page?: number;
      page_size?: number;
      country?: string;
      region?: string;
      program_family?: string;
      camp_type?: string;
      ages_min?: number;
      ages_max?: number;
      grades_min?: number;
      grades_max?: number;
      price_max?: number;
      overnight?: boolean;
      q?: string;
    }): Promise<CampListResponse> {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.country) qs.set("country", params.country);
      if (params?.region) qs.set("region", params.region);
      if (params?.program_family) qs.set("program_family", params.program_family);
      if (params?.camp_type) qs.set("camp_type", params.camp_type);
      if (params?.ages_min) qs.set("ages_min", String(params.ages_min));
      if (params?.ages_max) qs.set("ages_max", String(params.ages_max));
      if (params?.grades_min) qs.set("grades_min", String(params.grades_min));
      if (params?.grades_max) qs.set("grades_max", String(params.grades_max));
      if (params?.price_max) qs.set("price_max", String(params.price_max));
      if (params?.overnight !== undefined) qs.set("overnight", String(params.overnight));
      if (params?.q) qs.set("q", params.q);
      const query = qs.toString();
      return request(query ? `/api/camps?${query}` : "/api/camps", {}, true);
    },
    get(recordId: string): Promise<Camp> {
      return request(`/api/camps/${encodeURIComponent(recordId)}`);
    },
    stats(): Promise<CampStats> {
      return request("/api/camps/stats", {}, true);
    },
    moderate(recordId: string, payload: CampModerationPayload): Promise<Camp> {
      return request(`/api/camps/${encodeURIComponent(recordId)}/moderation`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    enrich(recordId: string, payload: CampEnrichmentPayload): Promise<Camp> {
      return request(`/api/camps/${encodeURIComponent(recordId)}/enrich`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    plans(recordId: string): Promise<CampPlanMembership[]> {
      return request(`/api/camps/${encodeURIComponent(recordId)}/plans`);
    },
  },

  favorites: {
    list(): Promise<Favorite[]> {
      return request("/api/favorites/");
    },
    add(campId: number, notes?: string): Promise<Favorite> {
      return request("/api/favorites/", {
        method: "POST",
        body: JSON.stringify({ camp_id: campId, notes: notes ?? "" }),
      });
    },
    update(campId: number, notes: string): Promise<Favorite> {
      return request(`/api/favorites/${campId}`, {
        method: "PATCH",
        body: JSON.stringify({ notes }),
      });
    },
    remove(campId: number): Promise<void> {
      return request(`/api/favorites/${campId}`, { method: "DELETE" });
    },
  },

  scrape: {
    extract(url: string): Promise<ScrapeResult> {
      return request("/api/scrape/", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
    },
  },

  plans: {
    list(): Promise<SummerPlan[]> {
      return request("/api/plans/");
    },
    get(id: number): Promise<SummerPlan> {
      return request(`/api/plans/${id}`);
    },
    create(payload: { title: string; description?: string; year: number }): Promise<SummerPlan> {
      return request("/api/plans/", { method: "POST", body: JSON.stringify(payload) });
    },
    update(id: number, payload: Partial<SummerPlan>): Promise<SummerPlan> {
      return request(`/api/plans/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    },
    shortlist(planId: number, status?: string): Promise<ShortlistItem[]> {
      const qs = status ? `?status=${status}` : "";
      return request(`/api/plans/${planId}/shortlist${qs}`);
    },
    addToShortlist(planId: number, payload: {
      camp_id?: number;
      custom_camp_name?: string;
      custom_camp_url?: string;
      status?: string;
    }): Promise<ShortlistItem> {
      return request(`/api/plans/${planId}/shortlist`, {
        method: "POST",
        body: JSON.stringify({ plan_id: planId, ...payload }),
      });
    },
    updateItem(itemId: number, payload: { status?: string; custom_camp_name?: string; custom_camp_url?: string }): Promise<ShortlistItem> {
      return request(`/api/plans/shortlist/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    removeItem(itemId: number): Promise<void> {
      return request(`/api/plans/shortlist/${itemId}`, { method: "DELETE" });
    },
    addNote(itemId: number, body: string, sourceUrl?: string): Promise<ShortlistNote> {
      return request(`/api/plans/shortlist/${itemId}/notes`, {
        method: "POST",
        body: JSON.stringify({ body, source_url: sourceUrl }),
      });
    },
    deleteNote(noteId: number): Promise<void> {
      return request(`/api/plans/notes/${noteId}`, { method: "DELETE" });
    },
    clipboard(planId: number): Promise<ResearchClipboard> {
      return request(`/api/plans/${planId}/clipboard`);
    },
    importResearch(planId: number, items: { name: string; notes: string; source_url?: string }[]): Promise<{ imported: number; total_in_payload: number }> {
      return request(`/api/plans/${planId}/import-research`, {
        method: "POST",
        body: JSON.stringify({ items }),
      });
    },
  },
};
