"use client";

import { Suspense, useCallback, useEffect, useRef, useState, startTransition, type FormEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  api,
  ApiError,
  Camp,
  CampListResponse,
  CampStats,
  ShortlistItem,
  ShortlistStatus,
  SummerPlan,
} from "@/lib/api";

const PAGE_SIZE = 25;

const COUNTRY_LABELS: Record<string, string> = {
  US: "United States",
  CA: "Canada",
  MX: "Mexico",
};

const PRICE_OPTIONS = [
  { value: "500", label: "Under $500" },
  { value: "1000", label: "Under $1,000" },
  { value: "2500", label: "Under $2,500" },
  { value: "5000", label: "Under $5,000" },
  { value: "10000", label: "Under $10,000" },
];

const FACET_LABEL_OVERRIDES: Record<string, string> = {
  "4 h": "4-H",
  ai: "AI",
  esl: "ESL",
  steam: "STEAM",
  stem: "STEM",
  ymca: "YMCA",
  "college pre college": "Pre-College",
  "faith based camps and retreats": "Faith-Based Retreats",
  "research program": "Research Program",
  "residential academic": "Residential Academic",
  "traditional overnight camps": "Traditional Overnight Camps",
};

const LOW_SIGNAL_TAGS = new Set([
  "overnight",
  "residential",
  "residential overnight",
  "overnight residential",
  "unknown",
]);

const SHORTLIST_STATUS_LABELS: Record<ShortlistStatus, string> = {
  interested: "Interested",
  researching: "Researching",
  applied: "Applied",
  going: "Going",
  passed: "Passed",
};

const SHORTLIST_STATUS_COLORS: Record<ShortlistStatus, string> = {
  interested: "bg-amber-50 text-amber-700 ring-amber-200",
  researching: "bg-sky-50 text-sky-700 ring-sky-200",
  applied: "bg-violet-50 text-violet-700 ring-violet-200",
  going: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  passed: "bg-slate-100 text-slate-600 ring-slate-200",
};

const EMPTY_SHORTLIST_MAP = new Map<number, ShortlistItem>();

function parseJsonArray(value: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function parsePositiveInt(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function toPositiveNumber(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value) || value <= 0) return null;
  return value;
}

function normalizeFacetValue(value: string): string {
  return value.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
}

function humanizeFacet(value: string): string {
  const normalized = normalizeFacetValue(value);
  const override = FACET_LABEL_OVERRIDES[normalized];
  if (override) return override;

  return normalized
    .split(" ")
    .map((word) => {
      if (!word) return word;
      if (word.length <= 3 && /[0-9]/.test(word)) return word.toUpperCase();
      if (["and", "of", "for"].includes(word)) return word;
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

function formatCountry(code: string | null | undefined): string | null {
  if (!code) return null;
  return COUNTRY_LABELS[code] ?? code;
}

function formatCount(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US").format(value);
}

function formatLocation(camp: Camp): string {
  const parts = [camp.city, camp.region, formatCountry(camp.country)].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Location not confirmed";
}

function normalizeComparableText(value: string | null | undefined): string {
  return (value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function formatCurrencyValue(amount: number, currency: string | null | undefined): string {
  const normalizedCurrency = currency && currency.length === 3 ? currency.toUpperCase() : "USD";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: normalizedCurrency,
      maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
    }).format(amount);
  } catch {
    return `$${amount.toLocaleString("en-US")}`;
  }
}

function formatPriceRange(camp: Camp): string | null {
  const min = toPositiveNumber(camp.pricing_min);
  const max = toPositiveNumber(camp.pricing_max);
  if (!min && !max) return null;
  if (min && max && min !== max) {
    return `${formatCurrencyValue(min, camp.pricing_currency)}-${formatCurrencyValue(max, camp.pricing_currency)}`;
  }
  return formatCurrencyValue(min ?? max ?? 0, camp.pricing_currency);
}

function formatAgeRange(camp: Camp): string | null {
  const min = toPositiveNumber(camp.ages_min);
  const max = toPositiveNumber(camp.ages_max);
  if (!min && !max) return null;
  if (min && max && min !== max) return `Ages ${min}-${max}`;
  return `Age ${min ?? max}`;
}

function formatGradeRange(camp: Camp): string | null {
  const min = toPositiveNumber(camp.grades_min);
  const max = toPositiveNumber(camp.grades_max);
  if (!min && !max) return null;
  if (min && max && min !== max) return `Grades ${min}-${max}`;
  return `Grade ${min ?? max}`;
}

function formatDurationRange(camp: Camp): string | null {
  const min = toPositiveNumber(camp.duration_min_days);
  const max = toPositiveNumber(camp.duration_max_days);
  if (!min && !max) return null;
  if (min && max && min !== max) return `${min}-${max} days`;
  const value = min ?? max;
  return value === 1 ? "1 day" : `${value} days`;
}

function formatBudgetLabel(value: number | null): string | null {
  if (!value) return null;
  const option = PRICE_OPTIONS.find((item) => Number(item.value) === value);
  return option?.label ?? `Under ${formatCurrencyValue(value, "USD")}`;
}

function buildPlanTargetLabel(plan: SummerPlan | null): string | null {
  if (!plan) return null;
  const parts: string[] = [];
  if (plan.target_age != null) parts.push(`Age ${plan.target_age}`);
  if (plan.target_grade != null) parts.push(`Grade ${plan.target_grade}`);
  return parts.length > 0 ? parts.join(" · ") : null;
}

function collectCampTags(camp: Camp): Array<{ label: string; tone: "family" | "neutral" }> {
  const tags: Array<{ label: string; tone: "family" | "neutral" }> = [];
  const seen = new Set<string>();

  for (const family of parseJsonArray(camp.program_family)) {
    const normalized = normalizeFacetValue(family);
    if (!normalized || LOW_SIGNAL_TAGS.has(normalized) || seen.has(normalized)) continue;
    seen.add(normalized);
    tags.push({ label: humanizeFacet(family), tone: "family" });
  }

  for (const type of parseJsonArray(camp.camp_types)) {
    const normalized = normalizeFacetValue(type);
    if (!normalized || LOW_SIGNAL_TAGS.has(normalized) || seen.has(normalized)) continue;
    seen.add(normalized);
    tags.push({ label: humanizeFacet(type), tone: "neutral" });
  }

  return tags.slice(0, 6);
}

export default function CampCatalogPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-sm text-slate-500">Loading camp catalog…</div>}>
      <CampCatalogInner />
    </Suspense>
  );
}

function CampCatalogInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();
  const searchFormRef = useRef<HTMLFormElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const addToPlanId = searchParams.get("addToPlan");
  const requestedPlanId = addToPlanId ? Number(addToPlanId) : null;
  const planIdIsValid = requestedPlanId != null && Number.isFinite(requestedPlanId) && requestedPlanId > 0;
  const page = parsePositiveInt(searchParams.get("page")) ?? 1;
  const search = searchParams.get("q") ?? "";
  const country = (searchParams.get("country") ?? "").toUpperCase();
  const region = (searchParams.get("region") ?? "").toUpperCase();
  const programFamily = searchParams.get("program_family") ?? "";
  const priceMax = parsePositiveInt(searchParams.get("price_max"));
  const overnightOnly = searchParams.get("overnight") === "1";
  const ageMatchEnabled = searchParams.get("age_match") !== "0";

  const [data, setData] = useState<CampListResponse | null>(null);
  const [stats, setStats] = useState<CampStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadedPlanState, setLoadedPlanState] = useState<{
    planId: number | null;
    plan: SummerPlan | null;
    error: string;
  }>({
    planId: null,
    plan: null,
    error: "",
  });
  const [shortlistState, setShortlistState] = useState<{
    planId: number | null;
    items: Map<number, ShortlistItem>;
  }>({
    planId: null,
    items: EMPTY_SHORTLIST_MAP,
  });

  const planContext =
    user && planIdIsValid && loadedPlanState.planId === requestedPlanId ? loadedPlanState.plan : null;
  const planState: "idle" | "loading" | "ready" | "sign_in_required" | "error" =
    !addToPlanId
      ? "idle"
      : authLoading
        ? "loading"
        : !user
          ? "sign_in_required"
          : !planIdIsValid
            ? "error"
            : loadedPlanState.planId !== requestedPlanId
              ? "loading"
              : loadedPlanState.plan
                ? "ready"
                : loadedPlanState.error
                  ? "error"
                  : "loading";
  const planError =
    !addToPlanId
      ? ""
      : !planIdIsValid
        ? "Plan link is invalid."
        : loadedPlanState.planId === requestedPlanId
          ? loadedPlanState.error
          : "";
  const shortlistMap =
    planContext && shortlistState.planId === planContext.id ? shortlistState.items : EMPTY_SHORTLIST_MAP;

  const updateQuery = useCallback((updates: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString());

    for (const [key, value] of Object.entries(updates)) {
      if (!value) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    }

    if (params.get("page") === "1") {
      params.delete("page");
    }

    const nextQuery = params.toString();
    const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;

    startTransition(() => {
      router.replace(nextUrl, { scroll: false });
    });
  }, [pathname, router, searchParams]);

  const refreshShortlist = useCallback(async (planId: number) => {
    const items = await api.plans.shortlist(planId);
    const nextMap = new Map<number, ShortlistItem>();
    for (const item of items) {
      if (item.camp_id != null) nextMap.set(item.camp_id, item);
    }
    return nextMap;
  }, []);

  useEffect(() => {
    if (!planIdIsValid || authLoading || !user || requestedPlanId == null) return;

    let cancelled = false;

    api.plans
      .get(requestedPlanId)
      .then((plan) => {
        if (cancelled) return;
        setLoadedPlanState({
          planId: requestedPlanId,
          plan,
          error: "",
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setLoadedPlanState({
          planId: requestedPlanId,
          plan: null,
          error:
            error instanceof ApiError && error.status === 401
              ? "Sign in to open this plan."
              : error instanceof Error
                ? error.message
                : "Unable to load that plan.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [authLoading, planIdIsValid, requestedPlanId, user]);

  useEffect(() => {
    if (!planContext) return;

    let cancelled = false;

    refreshShortlist(planContext.id)
      .then((items) => {
        if (cancelled) return;
        setShortlistState({
          planId: planContext.id,
          items,
        });
      })
      .catch(() => {
        if (cancelled) return;
        setShortlistState({
          planId: planContext.id,
          items: new Map(),
        });
      });

    return () => {
      cancelled = true;
    };
  }, [planContext, refreshShortlist]);

  useEffect(() => {
    let cancelled = false;

    async function loadCamps() {
      setLoading(true);
      try {
        const applyPlanMatch =
          Boolean(planContext) &&
          ageMatchEnabled &&
          (planContext?.target_age != null || planContext?.target_grade != null);

        const result = await api.camps.list({
          page,
          page_size: PAGE_SIZE,
          q: search || undefined,
          country: country || undefined,
          region: region || undefined,
          program_family: programFamily || undefined,
          price_max: priceMax || undefined,
          overnight: overnightOnly ? true : undefined,
          ages_min: applyPlanMatch && planContext?.target_age != null ? planContext.target_age : undefined,
          ages_max: applyPlanMatch && planContext?.target_age != null ? planContext.target_age : undefined,
          grades_min: applyPlanMatch && planContext?.target_grade != null ? planContext.target_grade : undefined,
          grades_max: applyPlanMatch && planContext?.target_grade != null ? planContext.target_grade : undefined,
        });

        if (!cancelled) {
          setData(result);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load camps", error);
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadCamps();

    return () => {
      cancelled = true;
    };
  }, [ageMatchEnabled, country, overnightOnly, page, planContext, priceMax, programFamily, region, search]);

  useEffect(() => {
    api.camps.stats().then(setStats).catch(console.error);
  }, []);

  useEffect(() => {
    if (!data || loading) return;

    const totalPages = Math.max(1, Math.ceil(Math.max(data.total, 1) / PAGE_SIZE));
    if (page > totalPages) {
      updateQuery({ page: totalPages > 1 ? String(totalPages) : null });
    }
  }, [data, loading, page, updateQuery]);

  async function handleAddToPlan(campId: number) {
    if (!planContext) return;
    try {
      await api.plans.addToShortlist(planContext.id, { camp_id: campId });
    } catch {
      // Ignore duplicate insert races and refresh the source of truth.
    }
    const items = await refreshShortlist(planContext.id);
    setShortlistState({
      planId: planContext.id,
      items,
    });
  }

  async function handlePassCamp(itemId: number) {
    if (!planContext) return;
    await api.plans.updateItem(itemId, { status: "passed" });
    const items = await refreshShortlist(planContext.id);
    setShortlistState({
      planId: planContext.id,
      items,
    });
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const nextSearch = String(formData.get("q") ?? "").trim();
    updateQuery({
      q: nextSearch || null,
      page: null,
    });
  }

  function clearAllFilters() {
    if (searchInputRef.current) {
      searchInputRef.current.value = "";
    }
    updateQuery({
      q: null,
      country: null,
      region: null,
      program_family: null,
      price_max: null,
      overnight: null,
      age_match: null,
      page: null,
    });
  }

  const totalPages = data ? Math.max(1, Math.ceil(Math.max(data.total, 1) / PAGE_SIZE)) : 0;
  const resultStart = data && data.items.length > 0 ? (page - 1) * PAGE_SIZE + 1 : 0;
  const resultEnd = data && data.items.length > 0 ? resultStart + data.items.length - 1 : 0;

  const planTargetLabel = buildPlanTargetLabel(planContext);
  const planFilterActive =
    Boolean(planContext) &&
    ageMatchEnabled &&
    (planContext?.target_age != null || planContext?.target_grade != null);

  const countryEntries = stats
    ? Object.entries(stats.by_country).sort((a, b) => (COUNTRY_LABELS[a[0]] ?? a[0]).localeCompare(COUNTRY_LABELS[b[0]] ?? b[0]))
    : [];

  const regionSource = stats
    ? country
      ? stats.regions_by_country[country] ?? {}
      : stats.by_region
    : {};

  const regionEntries = Object.entries(regionSource).sort((a, b) => a[0].localeCompare(b[0]));

  const allFamilyEntries = stats
    ? Object.entries(stats.by_program_family)
        .filter(([value, count]) => count > 0 && normalizeFacetValue(value) !== "unknown")
        .sort((a, b) => b[1] - a[1] || humanizeFacet(a[0]).localeCompare(humanizeFacet(b[0])))
    : [];

  const visibleFamilyEntries =
    !programFamily || allFamilyEntries.some(([value]) => value === programFamily)
      ? allFamilyEntries.slice(0, 10)
      : [[programFamily, stats?.by_program_family[programFamily] ?? 0], ...allFamilyEntries.slice(0, 9)];

  const activeFilters: Array<{ label: string; clear: Record<string, string | null> }> = [];
  if (search) {
    activeFilters.push({
      label: `Search: ${search}`,
      clear: { q: null, page: null },
    });
  }
  if (country) {
    activeFilters.push({
      label: formatCountry(country) ?? country,
      clear: { country: null, region: null, page: null },
    });
  }
  if (region) {
    activeFilters.push({
      label: `Region: ${region}`,
      clear: { region: null, page: null },
    });
  }
  if (programFamily) {
    activeFilters.push({
      label: humanizeFacet(programFamily),
      clear: { program_family: null, page: null },
    });
  }
  if (priceMax) {
    activeFilters.push({
      label: formatBudgetLabel(priceMax) ?? `Under ${formatCurrencyValue(priceMax, "USD")}`,
      clear: { price_max: null, page: null },
    });
  }
  if (overnightOnly) {
    activeFilters.push({
      label: "Overnight confirmed",
      clear: { overnight: null, page: null },
    });
  }

  return (
    <div className="space-y-6 text-slate-900">
      <section className="overflow-hidden rounded-[28px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(37,99,235,0.16),_transparent_42%),linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] px-6 py-7 shadow-sm sm:px-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">Camp catalog</p>
            <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-slate-950 sm:text-[2.6rem]">
              Search the residential camp database with cleaner signals.
            </h1>
            <p className="max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
              Filter the curated catalog by destination, program family, budget, and plan fit instead of digging through raw search results.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[26rem]">
            <MetricCard label="Programs" value={formatCount(stats?.total)} />
            <MetricCard label="Countries" value={formatCount(stats ? Object.keys(stats.by_country).length : null)} />
            <MetricCard label="Regions" value={formatCount(stats ? Object.keys(stats.by_region).length : null)} />
            <MetricCard label="Families" value={formatCount(stats ? Object.keys(stats.by_program_family).length : null)} />
          </div>
        </div>
      </section>

      {addToPlanId && planState === "ready" && planContext && (
        <section className="rounded-[24px] border border-sky-200 bg-sky-50/80 px-5 py-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Planning mode</p>
              <h2 className="text-lg font-semibold text-slate-950">{planContext.title}</h2>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
                <span>{formatCount(data?.total ?? null)} matches in this view</span>
                <span className="hidden text-slate-300 sm:inline">•</span>
                <span>{formatCount(shortlistMap.size)} already on the plan</span>
                {planTargetLabel && (
                  <>
                    <span className="hidden text-slate-300 sm:inline">•</span>
                    <span>{planTargetLabel}</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {planTargetLabel && (
                <label className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white px-3 py-2 text-sm font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={ageMatchEnabled}
                    onChange={(event) => updateQuery({ age_match: event.target.checked ? null : "0", page: null })}
                    className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  Match plan age/grade
                </label>
              )}
              <Link
                href={`/plans/${planContext.id}`}
                className="inline-flex items-center rounded-full border border-sky-200 px-3 py-2 text-sm font-medium text-sky-700 transition-colors hover:bg-sky-100"
              >
                Back to plan
              </Link>
            </div>
          </div>
        </section>
      )}

      {addToPlanId && planState === "sign_in_required" && !authLoading && (
        <section className="rounded-[24px] border border-amber-200 bg-amber-50 px-5 py-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-900">Plan shortcuts require a signed-in account.</p>
              <p className="text-sm text-slate-600">
                You can keep browsing the public catalog here, but adding camps directly to a plan needs authentication.
              </p>
            </div>
            <Link
              href="/login"
              className="inline-flex items-center rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
            >
              Sign in
            </Link>
          </div>
        </section>
      )}

      {addToPlanId && planState === "error" && (
        <section className="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 shadow-sm">
          <p className="text-sm font-semibold text-rose-700">Plan tools are unavailable right now.</p>
          <p className="mt-1 text-sm text-slate-600">{planError || "Unable to load that plan."}</p>
        </section>
      )}

      <section className="rounded-[26px] border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">
        <form ref={searchFormRef} onSubmit={handleSearchSubmit} className="flex flex-col gap-3 lg:flex-row">
          <label className="relative flex-1">
            <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-sm text-slate-400">Search</span>
            <input
              key={search}
              ref={searchInputRef}
              name="q"
              type="text"
              defaultValue={search}
              placeholder="Camp name, city, or operator"
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 pl-20 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
            />
          </label>
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Search
          </button>
          <button
            type="button"
            onClick={() => {
              searchFormRef.current?.reset();
              if (searchInputRef.current) {
                searchInputRef.current.value = "";
                searchInputRef.current.focus();
              }
              updateQuery({ q: null, page: null });
            }}
            className="inline-flex items-center justify-center rounded-2xl border border-slate-300 px-5 py-3 text-sm font-medium text-slate-600 transition hover:border-slate-400 hover:text-slate-900"
          >
            Clear
          </button>
        </form>

        <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-900">Destination</p>
                <p className="text-xs text-slate-500">Pick a country first, then narrow to a region.</p>
              </div>
              {country && (
                <button
                  type="button"
                  onClick={() => updateQuery({ country: null, region: null, page: null })}
                  className="text-xs font-medium text-slate-500 transition hover:text-slate-900"
                >
                  Clear country
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => updateQuery({ country: null, region: null, page: null })}
                className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                  !country
                    ? "bg-slate-900 text-white"
                    : "border border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                }`}
              >
                All countries
              </button>
              {countryEntries.map(([value, count]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() =>
                    updateQuery({
                      country: country === value ? null : value,
                      region: null,
                      page: null,
                    })
                  }
                  className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                    country === value
                      ? "bg-slate-900 text-white"
                      : "border border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                  }`}
                >
                  {formatCountry(value) ?? value} <span className="text-current/70">{formatCount(count)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-900">Region</span>
              <select
                value={region}
                onChange={(event) => updateQuery({ region: event.target.value || null, page: null })}
                className="w-full rounded-2xl border border-slate-300 bg-white px-3 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
              >
                <option value="">{country ? "All regions in country" : "All regions"}</option>
                {regionEntries.map(([value, count]) => (
                  <option key={value} value={value}>
                    {value} ({count})
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-900">Budget</span>
              <select
                value={priceMax ? String(priceMax) : ""}
                onChange={(event) => updateQuery({ price_max: event.target.value || null, page: null })}
                className="w-full rounded-2xl border border-slate-300 bg-white px-3 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
              >
                <option value="">Any budget</option>
                {PRICE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="space-y-2">
              <span className="text-sm font-medium text-slate-900">Signals</span>
              <div className="flex h-full flex-col justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={overnightOnly}
                    onChange={(event) => updateQuery({ overnight: event.target.checked ? "1" : null, page: null })}
                    className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  Overnight confirmed only
                </label>
                {planTargetLabel && planState === "ready" && (
                  <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={ageMatchEnabled}
                      onChange={(event) => updateQuery({ age_match: event.target.checked ? null : "0", page: null })}
                      className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                    />
                    Match {planTargetLabel}
                  </label>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-900">Program family</p>
                <p className="text-xs text-slate-500">Start broad here, then narrow by place or price.</p>
              </div>
              {programFamily && (
                <button
                  type="button"
                  onClick={() => updateQuery({ program_family: null, page: null })}
                  className="text-xs font-medium text-slate-500 transition hover:text-slate-900"
                >
                  Clear family
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => updateQuery({ program_family: null, page: null })}
                className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                  !programFamily
                    ? "bg-slate-900 text-white"
                    : "border border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                }`}
              >
                All families
              </button>
              {visibleFamilyEntries.map(([value, count]) => {
                const familyValue = String(value);
                const familyCount = Number(count);

                return (
                <button
                  key={familyValue}
                  type="button"
                  onClick={() =>
                    updateQuery({
                      program_family: programFamily === familyValue ? null : familyValue,
                      page: null,
                    })
                  }
                  className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                    programFamily === familyValue
                      ? "bg-slate-900 text-white"
                      : "border border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                  }`}
                >
                  {humanizeFacet(familyValue)} <span className="text-current/70">{formatCount(familyCount)}</span>
                </button>
                );
              })}
            </div>
          </div>

          {activeFilters.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-4">
              {activeFilters.map((filter) => (
                <ActiveFilterChip key={filter.label} label={filter.label} onRemove={() => updateQuery(filter.clear)} />
              ))}
              <button
                type="button"
                onClick={clearAllFilters}
                className="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="rounded-[24px] border border-slate-200 bg-slate-50/70 px-4 py-4 shadow-sm sm:px-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-900">
              {loading
                ? "Refreshing camps…"
                : data && data.total > 0
                  ? `Showing ${resultStart}-${resultEnd} of ${formatCount(data.total)}`
                  : "No camps match this view"}
            </p>
            <p className="text-sm text-slate-600">
              {country
                ? `Focused on ${formatCountry(country)}${region ? ` · ${region}` : ""}.`
                : "Search across the full public catalog."}
              {programFamily ? ` ${humanizeFacet(programFamily)} is selected.` : ""}
              {planFilterActive ? ` Matching ${planTargetLabel}.` : ""}
            </p>
          </div>
          {data && data.total > 0 && (
            <div className="text-sm text-slate-500">
              Page {page} of {totalPages}
            </div>
          )}
        </div>
      </section>

      {loading ? (
        <div className="py-16 text-center text-sm text-slate-500">Loading camps…</div>
      ) : !data || data.items.length === 0 ? (
        <EmptyResults onClear={activeFilters.length > 0 ? clearAllFilters : undefined} />
      ) : (
        <>
          <div className="space-y-3">
            {data.items.map((camp) => (
              <CampRow
                key={camp.id}
                camp={camp}
                shortlistItem={shortlistMap.get(camp.id)}
                canManagePlan={Boolean(planContext && planState === "ready")}
                onAdd={() => handleAddToPlan(camp.id)}
                onPass={() => {
                  const shortlistItem = shortlistMap.get(camp.id);
                  if (shortlistItem) {
                    void handlePassCamp(shortlistItem.id);
                  }
                }}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex flex-col items-center justify-between gap-3 rounded-[24px] border border-slate-200 bg-white px-4 py-4 shadow-sm sm:flex-row">
              <button
                type="button"
                onClick={() => updateQuery({ page: page > 2 ? String(page - 1) : null })}
                disabled={page <= 1}
                className="inline-flex w-full items-center justify-center rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-45 sm:w-auto"
              >
                Previous page
              </button>
              <span className="text-sm text-slate-500">
                {resultStart}-{resultEnd} of {formatCount(data.total)}
              </span>
              <button
                type="button"
                onClick={() => updateQuery({ page: String(Math.min(totalPages, page + 1)) })}
                disabled={page >= totalPages}
                className="inline-flex w-full items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-45 sm:w-auto"
              >
                Next page
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/80 px-4 py-3 backdrop-blur">
      <div className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{value}</div>
    </div>
  );
}

function ActiveFilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <button
      type="button"
      onClick={onRemove}
      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
    >
      <span>{label}</span>
      <span className="text-slate-400">×</span>
    </button>
  );
}

function MetaPill({ label }: { label: string }) {
  return (
    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
      {label}
    </span>
  );
}

function TagPill({ label, tone }: { label: string; tone: "family" | "neutral" }) {
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-medium ${
        tone === "family"
          ? "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200"
          : "bg-slate-100 text-slate-600"
      }`}
    >
      {label}
    </span>
  );
}

function EmptyResults({ onClear }: { onClear?: () => void }) {
  return (
    <section className="rounded-[24px] border border-dashed border-slate-300 bg-white px-5 py-14 text-center shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">No camps match those filters.</h2>
      <p className="mt-2 text-sm text-slate-600">
        Try widening the budget, clearing the family filter, or broadening the destination.
      </p>
      {onClear && (
        <button
          type="button"
          onClick={onClear}
          className="mt-5 inline-flex items-center rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          Clear filters
        </button>
      )}
    </section>
  );
}

function CampRow({
  camp,
  shortlistItem,
  canManagePlan,
  onAdd,
  onPass,
}: {
  camp: Camp;
  shortlistItem?: ShortlistItem;
  canManagePlan: boolean;
  onAdd: () => void;
  onPass: () => void;
}) {
  const title = camp.display_name || camp.name;
  const location = formatLocation(camp);
  const ageLabel = formatAgeRange(camp);
  const gradeLabel = formatGradeRange(camp);
  const durationLabel = formatDurationRange(camp);
  const priceLabel = formatPriceRange(camp);
  const tags = collectCampTags(camp);
  const operatorName =
    camp.operator_name &&
    normalizeComparableText(camp.operator_name) !== normalizeComparableText(title)
      ? camp.operator_name
      : null;

  return (
    <article className="rounded-[24px] border border-slate-200 bg-white px-4 py-4 shadow-sm transition hover:-translate-y-px hover:shadow-md [content-visibility:auto] sm:px-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-start gap-3">
            <div className="min-w-0 flex-1">
              <Link
                href={`/camps/${encodeURIComponent(camp.record_id)}`}
                className="inline-block text-lg font-semibold tracking-tight text-slate-950 transition hover:text-sky-700"
              >
                {title}
              </Link>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600">
                <span>{location}</span>
                {operatorName && (
                  <>
                    <span className="text-slate-300">•</span>
                    <span>{operatorName}</span>
                  </>
                )}
              </div>
            </div>
            {camp.overnight_confirmed && (
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
                Overnight confirmed
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {ageLabel && <MetaPill label={ageLabel} />}
            {gradeLabel && <MetaPill label={gradeLabel} />}
            {durationLabel && <MetaPill label={durationLabel} />}
            {priceLabel && <MetaPill label={priceLabel} />}
          </div>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <TagPill key={`${tag.tone}-${tag.label}`} label={tag.label} tone={tag.tone} />
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2 lg:min-w-[12rem] lg:items-end">
          <Link
            href={`/camps/${encodeURIComponent(camp.record_id)}`}
            className="inline-flex items-center justify-center rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:text-slate-950"
          >
            View details
          </Link>

          {canManagePlan &&
            (shortlistItem ? (
              <div className="flex flex-col items-stretch gap-2 lg:items-end">
                <span
                  className={`inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${SHORTLIST_STATUS_COLORS[shortlistItem.status]}`}
                >
                  {SHORTLIST_STATUS_LABELS[shortlistItem.status]}
                </span>
                {shortlistItem.status !== "passed" && (
                  <button
                    type="button"
                    onClick={onPass}
                    className="text-sm font-medium text-slate-500 transition hover:text-slate-900"
                  >
                    Mark as passed
                  </button>
                )}
              </div>
            ) : (
              <button
                type="button"
                onClick={onAdd}
                className="inline-flex items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                Add to plan
              </button>
            ))}
        </div>
      </div>
    </article>
  );
}
