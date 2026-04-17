export interface ContributionPrefill {
  recordId?: string;
  campName?: string;
  websiteUrl?: string;
  country?: string;
  region?: string;
  city?: string;
  venueName?: string;
}

type SearchParamReader = {
  get(name: string): string | null;
};

export function buildContributionPrefillQuery(prefill: ContributionPrefill): string {
  const qs = new URLSearchParams();
  if (prefill.recordId) qs.set("recordId", prefill.recordId);
  if (prefill.campName) qs.set("campName", prefill.campName);
  if (prefill.websiteUrl) qs.set("websiteUrl", prefill.websiteUrl);
  if (prefill.country) qs.set("country", prefill.country);
  if (prefill.region) qs.set("region", prefill.region);
  if (prefill.city) qs.set("city", prefill.city);
  if (prefill.venueName) qs.set("venueName", prefill.venueName);
  return qs.toString();
}

export function readContributionPrefill(searchParams: SearchParamReader | null): ContributionPrefill {
  if (!searchParams) return {};
  return {
    recordId: searchParams.get("recordId") || undefined,
    campName: searchParams.get("campName") || undefined,
    websiteUrl: searchParams.get("websiteUrl") || undefined,
    country: searchParams.get("country") || undefined,
    region: searchParams.get("region") || undefined,
    city: searchParams.get("city") || undefined,
    venueName: searchParams.get("venueName") || undefined,
  };
}

export function hasContributionPrefill(prefill: ContributionPrefill): boolean {
  return Boolean(
    prefill.recordId ||
      prefill.campName ||
      prefill.websiteUrl ||
      prefill.country ||
      prefill.region ||
      prefill.city ||
      prefill.venueName
  );
}

export function buildContributionPrefillNotes(prefill: ContributionPrefill): string {
  const target = prefill.campName || prefill.recordId;
  if (!target) return "";
  if (prefill.recordId) {
    return `Update or add evidence for published catalog record ${target} (${prefill.recordId}).`;
  }
  return `Add details or corrections for ${target}.`;
}
