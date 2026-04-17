"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, Camp } from "@/lib/api";
import FavoriteButton from "@/components/FavoriteButton";

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
  const params = useParams();
  const recordId = params.id as string;
  const [camp, setCamp] = useState<Camp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
        </div>
      </div>

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
