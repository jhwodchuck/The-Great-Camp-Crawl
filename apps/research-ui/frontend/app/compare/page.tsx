"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, Favorite } from "@/lib/api";

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

function CompareContent() {
  const { user, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids");
  const campIds = idsParam ? idsParam.split(",").map(Number).filter(Boolean) : [];

  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;
    api.favorites.list()
      .then(favs => {
        if (campIds.length > 0) {
          setFavorites(favs.filter(f => campIds.includes(f.camp_id)));
        } else {
          setFavorites(favs);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user, authLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  if (authLoading || loading) return <div className="text-gray-400 dark:text-gray-500 text-center mt-20">Loading...</div>;
  if (!user) return <div className="text-gray-400 dark:text-gray-500 text-center mt-20">Please log in to compare camps.</div>;

  const camps = favorites.map(f => ({ ...f.camp, notes: f.notes }));

  if (camps.length < 2) {
    return (
      <div className="text-center py-12 text-gray-400 space-y-2">
        <p className="text-lg">Select at least 2 favorites to compare.</p>
        <Link href="/favorites" className="text-blue-600 hover:underline">Go to Favorites →</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 text-gray-900 dark:text-gray-100">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">⚖️ Compare Camps</h1>
        <Link href="/favorites" className="text-blue-600 dark:text-blue-400 hover:underline text-sm">← Favorites</Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full bg-white dark:bg-gray-900 rounded-xl shadow text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left px-4 py-3 text-gray-500 dark:text-gray-400 font-medium w-36">Attribute</th>
              {camps.map(c => (
                <th key={c.id} className="text-left px-4 py-3 font-bold text-gray-800 dark:text-gray-100 min-w-[200px]">
                  <Link href={`/camps/${encodeURIComponent(c.record_id)}`} className="hover:text-blue-600 dark:hover:text-blue-400">
                    {c.display_name || c.name}
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <CompareRow label="Location" values={camps.map(c => [c.city, c.region, c.country].filter(Boolean).join(", "))} />
            <CompareRow label="Ages" values={camps.map(c =>
              (c.ages_min || c.ages_max) ? `${c.ages_min ?? "?"}–${c.ages_max ?? "?"}` : "—"
            )} />
            <CompareRow label="Grades" values={camps.map(c =>
              (c.grades_min || c.grades_max) ? `${c.grades_min ?? "?"}–${c.grades_max ?? "?"}` : "—"
            )} />
            <CompareRow label="Pricing" values={camps.map(c =>
              (c.pricing_min || c.pricing_max)
                ? `${c.pricing_currency || "USD"} $${c.pricing_min ?? "?"}–$${c.pricing_max ?? "?"}`
                : "—"
            )} />
            <CompareRow label="Duration" values={camps.map(c =>
              (c.duration_min_days || c.duration_max_days)
                ? `${c.duration_min_days ?? "?"}–${c.duration_max_days ?? "?"} days`
                : "—"
            )} />
            <CompareRow label="Overnight" values={camps.map(c => c.overnight_confirmed ? "✅ Yes" : "—")} />
            <CompareRow label="Active" values={camps.map(c => c.active_confirmed ? "✅ Yes" : "—")} />
            <CompareRow label="Program Family" values={camps.map(c =>
              parseJsonArray(c.program_family).map(formatProgramFamily).join(", ") || "—"
            )} />
            <CompareRow label="Types" values={camps.map(c =>
              parseJsonArray(c.camp_types).join(", ") || "—"
            )} />
            <CompareRow label="Operator" values={camps.map(c => c.operator_name || "—")} />
            <CompareRow label="Website" values={camps.map(c => c.website_url || "—")} isLink />
            <CompareRow label="Contact" values={camps.map(c =>
              [c.contact_email, c.contact_phone].filter(Boolean).join(" / ") || "—"
            )} />
            <CompareRow label="Confidence" values={camps.map(c => c.confidence || "—")} />
            <CompareRow label="Your Notes" values={camps.map(c => c.notes || "—")} isNotes />
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CompareRow({ label, values, isLink, isNotes }: {
  label: string;
  values: string[];
  isLink?: boolean;
  isNotes?: boolean;
}) {
  return (
    <tr className="border-b border-gray-200 dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800">
      <td className="px-4 py-2.5 font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">{label}</td>
      {values.map((v, i) => (
        <td key={i} className={`px-4 py-2.5 text-gray-700 dark:text-gray-200 ${isNotes ? "italic text-gray-500 dark:text-gray-400" : ""}`}>
          {isLink && v !== "—" ? (
            <a href={v} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all text-xs">
              {v}
            </a>
          ) : v}
        </td>
      ))}
    </tr>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="text-gray-400 text-center mt-20">Loading...</div>}>
      <CompareContent />
    </Suspense>
  );
}
