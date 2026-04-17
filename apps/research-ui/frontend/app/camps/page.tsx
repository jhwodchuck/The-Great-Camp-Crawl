"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Camp, CampListResponse, CampStats } from "@/lib/api";

const PAGE_SIZE = 25;

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

export default function CampCatalogPage() {
  const [data, setData] = useState<CampListResponse | null>(null);
  const [stats, setStats] = useState<CampStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  // Filters
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("");
  const [region, setRegion] = useState("");
  const [overnightOnly, setOvernightOnly] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadCamps() {
      setLoading(true);
      try {
        const result = await api.camps.list({
          page,
          page_size: PAGE_SIZE,
          q: search || undefined,
          country: country || undefined,
          region: region || undefined,
          overnight: overnightOnly ? true : undefined,
        });
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load camps", err);
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
  }, [page, search, country, region, overnightOnly]);

  useEffect(() => {
    api.camps.stats().then(setStats).catch(console.error);
  }, []);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">🏕️ Camp Catalog</h1>
        {stats && (
          <span className="text-sm text-gray-500">{stats.total} camps</span>
        )}
      </div>

      {/* Search + Filters */}
      <div className="bg-white rounded-2xl shadow p-4 space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="Search by name, city, or operator..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-3">
          <select
            value={country}
            onChange={e => { setCountry(e.target.value); setRegion(""); setPage(1); }}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">All Countries</option>
            {stats && Object.entries(stats.by_country)
              .sort(([, a], [, b]) => b - a)
              .map(([c, n]) => (
                <option key={c} value={c}>{c} ({n})</option>
              ))}
          </select>

          <select
            value={region}
            onChange={e => { setRegion(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">All Regions</option>
            {stats && Object.entries(stats.by_region)
              .filter(([r]) => !country || (data?.items.some(c => c.country === country && c.region === r)))
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([r, n]) => (
                <option key={r} value={r}>{r} ({n})</option>
              ))}
          </select>

          <label className="flex items-center gap-1.5 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={overnightOnly}
              onChange={e => { setOvernightOnly(e.target.checked); setPage(1); }}
              className="rounded"
            />
            Overnight only
          </label>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-gray-400 text-center py-12">Loading camps...</div>
      ) : !data || data.items.length === 0 ? (
        <div className="text-gray-400 text-center py-12">No camps found matching your filters.</div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {data.items.map(camp => (
              <CampCard key={camp.id} camp={camp} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-sm"
              >
                ← Prev
              </button>
              <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-sm"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CampCard({ camp }: { camp: Camp }) {
  const families = parseJsonArray(camp.program_family);
  const types = parseJsonArray(camp.camp_types);

  return (
    <Link
      href={`/camps/${encodeURIComponent(camp.record_id)}`}
      className="block bg-white rounded-xl shadow hover:shadow-md transition-shadow p-4 space-y-2"
    >
      <div className="flex items-start justify-between">
        <h3 className="font-bold text-gray-800 text-base leading-tight">
          {camp.display_name || camp.name}
        </h3>
        {camp.overnight_confirmed && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full whitespace-nowrap ml-2">
            🌙 Overnight
          </span>
        )}
      </div>

      <p className="text-sm text-gray-500">
        {[camp.city, camp.region, camp.country].filter(Boolean).join(", ")}
      </p>

      {/* Key stats row */}
      <div className="flex flex-wrap gap-2 text-xs text-gray-600">
        {(camp.ages_min || camp.ages_max) && (
          <span className="bg-blue-50 px-2 py-0.5 rounded">
            Ages {camp.ages_min ?? "?"}–{camp.ages_max ?? "?"}
          </span>
        )}
        {(camp.pricing_min || camp.pricing_max) && (
          <span className="bg-yellow-50 px-2 py-0.5 rounded">
            ${camp.pricing_min ?? "?"}–${camp.pricing_max ?? "?"}
          </span>
        )}
        {(camp.duration_min_days || camp.duration_max_days) && (
          <span className="bg-purple-50 px-2 py-0.5 rounded">
            {camp.duration_min_days ?? "?"}–{camp.duration_max_days ?? "?"} days
          </span>
        )}
      </div>

      {/* Tags */}
      {(families.length > 0 || types.length > 0) && (
        <div className="flex flex-wrap gap-1">
          {families.slice(0, 3).map(f => (
            <span key={f} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              {formatProgramFamily(f)}
            </span>
          ))}
          {types.slice(0, 3).map(t => (
            <span key={t} className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded italic">
              {t}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}
