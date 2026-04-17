"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, Camp } from "@/lib/api";
import FavoriteButton from "@/components/FavoriteButton";
import { useAuth } from "@/lib/auth";
import { buildContributionPrefillQuery } from "@/lib/contribution-prefill";

function parseJsonArray(val: string | null): string[] {
  if (!val) return [];
  try {
    const parsed = JSON.parse(val);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function formatProgramFamily(pf: string): string {
  return pf.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

export default function CampDetailPage() {
  const { user, loading: authLoading } = useAuth();
  const params = useParams();
  const recordId = params.id as string;
  const [camp, setCamp] = useState<Camp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [moderationReason, setModerationReason] = useState("not_a_camp");
  const [moderationNotes, setModerationNotes] = useState("");
  const [moderating, setModerating] = useState(false);
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    api.camps
      .get(recordId)
      .then(setCamp)
      .catch(err => setError(err.message || "Failed to load camp"))
      .finally(() => setLoading(false));
  }, [recordId]);

  if (loading) return <div className="text-gray-400 text-center mt-20">Loading...</div>;
  if (error) return <div className="text-red-400 text-center mt-20">{error}</div>;
  if (!camp) return <div className="text-gray-400 text-center mt-20">Camp not found</div>;

  const families = parseJsonArray(camp.program_family);
  const types = parseJsonArray(camp.camp_types);
  const contributionQuery = buildContributionPrefillQuery({
    recordId: camp.record_id,
    campName: camp.display_name || camp.name,
    websiteUrl: camp.website_url || undefined,
    country: camp.country || undefined,
    region: camp.region || undefined,
    city: camp.city || undefined,
    venueName: camp.venue_name || undefined,
  });
  const contributionHref = contributionQuery ? `/missions?${contributionQuery}` : "/missions";

  async function handleModeration(isExcluded: boolean) {
    setModerating(true);
    setActionError("");
    try {
      const updated = await api.camps.moderate(recordId, {
        is_excluded: isExcluded,
        reason: isExcluded ? moderationReason : undefined,
        notes: isExcluded ? moderationNotes : undefined,
      });
      setCamp(updated);
      if (!isExcluded) {
        setModerationNotes("");
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to update camp moderation");
    } finally {
      setModerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link href="/camps" className="text-blue-600 hover:underline text-sm">
        ← Back to Catalog
      </Link>

      {/* Header */}
      <div className="bg-white rounded-2xl shadow p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              🏕️ {camp.display_name || camp.name}
            </h1>
            <p className="text-gray-500 mt-1">
              {[camp.city, camp.region, camp.country].filter(Boolean).join(", ")}
            </p>
          </div>
          <FavoriteButton campId={camp.id} />
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2 mt-3">
          {camp.overnight_confirmed && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">🌙 Overnight Confirmed</span>
          )}
          {camp.active_confirmed && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">✅ Active</span>
          )}
          {camp.confidence && (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
              Confidence: {camp.confidence}
            </span>
          )}
          {camp.draft_status && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">
              {camp.draft_status}
            </span>
          )}
          {camp.is_excluded && (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full">
              Hidden: not a camp
            </span>
          )}
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
        <h2 className="text-lg font-bold text-blue-900">✏️ Add Or Correct Info</h2>
        <p className="text-sm text-blue-800 mt-2">
          Use a contribution draft to add evidence, fix missing details, or suggest a correction for this camp.
          Contributions are reviewed before they become part of the published research.
        </p>
        {authLoading ? (
          <p className="text-sm text-blue-700 mt-4">Checking your sign-in status…</p>
        ) : user ? (
          <div className="flex flex-wrap gap-3 mt-4">
            <Link
              href={contributionHref}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700"
            >
              Add Info Through a Mission
            </Link>
            <Link
              href="/contributions"
              className="bg-white text-blue-700 px-4 py-2 rounded-lg font-medium border border-blue-200 hover:bg-blue-100"
            >
              Open Contributions
            </Link>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3 mt-4">
            <Link
              href="/login"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700"
            >
              Sign In To Add Info
            </Link>
            <Link
              href="/register"
              className="bg-white text-blue-700 px-4 py-2 rounded-lg font-medium border border-blue-200 hover:bg-blue-100"
            >
              Create Contributor Account
            </Link>
          </div>
        )}
      </div>

      {user?.role === "parent" && (
        <div className={`rounded-2xl border p-6 ${camp.is_excluded ? "border-red-200 bg-red-50" : "border-orange-200 bg-orange-50"}`}>
          <h2 className={`text-lg font-bold ${camp.is_excluded ? "text-red-900" : "text-orange-900"}`}>
            {camp.is_excluded ? "🚫 Hidden From Public Catalog" : "🧹 Candidate Triage"}
          </h2>
          {camp.is_excluded ? (
            <>
              <p className="mt-2 text-sm text-red-800">
                This record is currently hidden as a non-camp or out-of-scope result.
              </p>
              {(camp.exclusion_reason || camp.exclusion_notes) && (
                <div className="mt-3 rounded-xl bg-white/70 p-4 text-sm text-red-900">
                  {camp.exclusion_reason && (
                    <p>
                      <span className="font-medium">Reason:</span> {formatModerationReason(camp.exclusion_reason)}
                    </p>
                  )}
                  {camp.exclusion_notes && (
                    <p className="mt-1 whitespace-pre-wrap">{camp.exclusion_notes}</p>
                  )}
                </div>
              )}
              <button
                onClick={() => handleModeration(false)}
                disabled={moderating}
                className="mt-4 rounded-lg bg-white px-4 py-2 font-medium text-red-700 border border-red-200 hover:bg-red-100 disabled:opacity-50"
              >
                {moderating ? "Restoring…" : "Restore To Catalog"}
              </button>
            </>
          ) : (
            <>
              <p className="mt-2 text-sm text-orange-800">
                If this is clearly junk, unrelated, or not an overnight/residential youth program, hide it from the public catalog here.
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-orange-900 mb-1">Reason</label>
                  <select
                    value={moderationReason}
                    onChange={e => setModerationReason(e.target.value)}
                    className="w-full rounded-lg border border-orange-200 bg-white px-3 py-2 text-sm"
                  >
                    <option value="not_a_camp">Not a camp</option>
                    <option value="not_overnight">Not overnight / not residential</option>
                    <option value="duplicate_or_wrong_venue">Duplicate or wrong venue</option>
                    <option value="inactive_or_out_of_scope">Inactive or out of scope</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="md:col-span-1">
                  <label className="block text-sm font-medium text-orange-900 mb-1">Notes</label>
                  <textarea
                    value={moderationNotes}
                    onChange={e => setModerationNotes(e.target.value)}
                    rows={3}
                    placeholder="Why this obviously should not stay in the public catalog…"
                    className="w-full rounded-lg border border-orange-200 bg-white px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <button
                onClick={() => handleModeration(true)}
                disabled={moderating}
                className="mt-4 rounded-lg bg-orange-600 px-4 py-2 font-medium text-white hover:bg-orange-700 disabled:opacity-50"
              >
                {moderating ? "Hiding…" : "Mark Not A Camp"}
              </button>
            </>
          )}
          {actionError && <p className="mt-3 text-sm text-red-700">{actionError}</p>}
        </div>
      )}

      {/* Key Details */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">📋 Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          {camp.operator_name && (
            <Detail label="Operator" value={camp.operator_name} />
          )}
          {camp.venue_name && (
            <Detail label="Venue" value={camp.venue_name} />
          )}
          {(camp.ages_min || camp.ages_max) && (
            <Detail label="Ages" value={`${camp.ages_min ?? "?"} – ${camp.ages_max ?? "?"}`} />
          )}
          {(camp.grades_min || camp.grades_max) && (
            <Detail label="Grades" value={`${camp.grades_min ?? "?"} – ${camp.grades_max ?? "?"}`} />
          )}
          {(camp.duration_min_days || camp.duration_max_days) && (
            <Detail label="Duration" value={`${camp.duration_min_days ?? "?"} – ${camp.duration_max_days ?? "?"} days`} />
          )}
          {(camp.pricing_min || camp.pricing_max) && (
            <Detail
              label="Pricing"
              value={`${camp.pricing_currency || "USD"} $${camp.pricing_min ?? "?"}–$${camp.pricing_max ?? "?"}`}
            />
          )}
          {camp.boarding_included !== null && (
            <Detail label="Boarding Included" value={camp.boarding_included ? "Yes" : "No"} />
          )}
          {camp.website_url && (
            <div>
              <span className="font-medium text-gray-700">Website: </span>
              <a
                href={camp.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline break-all"
              >
                {camp.website_url}
              </a>
            </div>
          )}
          {camp.contact_email && (
            <Detail label="Email" value={camp.contact_email} />
          )}
          {camp.contact_phone && (
            <Detail label="Phone" value={camp.contact_phone} />
          )}
          {camp.last_verified && (
            <Detail label="Last Verified" value={camp.last_verified} />
          )}
        </div>
      </div>

      {/* Program Types */}
      {(families.length > 0 || types.length > 0) && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-3">🎯 Program Types</h2>
          <div className="flex flex-wrap gap-2">
            {families.map(f => (
              <span key={f} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm">
                {formatProgramFamily(f)}
              </span>
            ))}
            {types.map(t => (
              <span key={t} className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm italic">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Description / Full Dossier */}
      {camp.description_md && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-3">📝 Full Dossier</h2>
          <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
            {camp.description_md}
          </div>
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="font-medium text-gray-700">{label}: </span>
      <span className="text-gray-600">{value}</span>
    </div>
  );
}

function formatModerationReason(reason: string): string {
  return reason.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}
