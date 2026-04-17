"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api, Mission, Contribution, ScrapeResult } from "@/lib/api";

export default function MissionDetailPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const missionId = Number(params.id);

  const [mission, setMission] = useState<Mission | null>(null);
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [fetching, setFetching] = useState(true);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newCamp, setNewCamp] = useState({ camp_name: "", website_url: "", region: "", city: "", overnight_confirmed: "unknown", notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scraping, setScraping] = useState(false);
  const [scrapeResult, setScrapeResult] = useState<ScrapeResult | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }
    Promise.all([
      api.missions.get(missionId),
      api.contributions.list({ mission_id: missionId }),
    ]).then(([m, cs]) => {
      setMission(m);
      setContributions(cs);
    }).finally(() => setFetching(false));
  }, [user, loading, missionId, router]);

  async function handleAddCamp(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const c = await api.contributions.create({
        mission_id: missionId,
        camp_name: newCamp.camp_name,
        website_url: newCamp.website_url || undefined,
        country: mission?.country || "US",
        region: newCamp.region || mission?.region || undefined,
        city: newCamp.city || undefined,
        overnight_confirmed: newCamp.overnight_confirmed,
        notes: newCamp.notes || undefined,
      });
      router.push(`/contributions/${c.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add camp");
      setSaving(false);
    }
  }

  async function handleScrape(e: React.FormEvent) {
    e.preventDefault();
    if (!scrapeUrl.trim()) return;
    setScraping(true);
    setError("");
    setScrapeResult(null);
    try {
      const result = await api.scrape.extract(scrapeUrl.trim());
      setScrapeResult(result);
      // Auto-fill the form fields from scrape results
      setNewCamp(prev => ({
        ...prev,
        camp_name: prev.camp_name || result.title || "",
        website_url: result.url || prev.website_url,
        overnight_confirmed: result.overnight_signals.length > 0 ? "yes" : prev.overnight_confirmed,
        notes: prev.notes || (result.description ? `From website: ${result.description}` : ""),
      }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to scrape URL");
    } finally {
      setScraping(false);
    }
  }

  if (loading || fetching) return <div className="text-gray-400 text-center mt-20">Loading…</div>;
  if (!mission) return <div className="text-red-400 text-center mt-20">Mission not found</div>;

  const statusColor: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    submitted: "bg-blue-100 text-blue-700",
    under_review: "bg-purple-100 text-purple-700",
    changes_requested: "bg-yellow-100 text-yellow-700",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/missions" className="text-blue-600 hover:underline text-sm">← Missions</Link>
      </div>

      <div className="bg-white rounded-2xl shadow p-6">
        <h1 className="text-2xl font-bold text-gray-800">{mission.title}</h1>
        {mission.description && <p className="text-gray-500 mt-2">{mission.description}</p>}
        <div className="flex flex-wrap gap-2 mt-3">
          {mission.country && <span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">{mission.country}</span>}
          {mission.region && <span className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5">{mission.region}</span>}
          {mission.program_family && <span className="text-xs bg-green-100 text-green-700 rounded px-2 py-0.5">{mission.program_family}</span>}
        </div>
      </div>

      {/* Child: Add a camp button */}
      {user?.role === "child" && (
        <div>
          {!showNewForm ? (
            <button onClick={() => setShowNewForm(true)} className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 text-lg">
              🏕️ Add a Camp I Found!
            </button>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
              <h2 className="font-bold text-blue-800 mb-4">Tell us about the camp you found! 🎉</h2>

              {/* Scrape URL auto-fill */}
              <form onSubmit={handleScrape} className="mb-4 p-3 bg-white rounded-lg border border-blue-100">
                <label className="block text-sm font-medium text-blue-700 mb-1">🔍 Paste a URL to auto-fill</label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={scrapeUrl}
                    onChange={e => setScrapeUrl(e.target.value)}
                    placeholder="https://camphappytrails.com"
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                  <button
                    type="submit"
                    disabled={scraping || !scrapeUrl.trim()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    {scraping ? "Scraping..." : "Auto-fill"}
                  </button>
                </div>
                {scrapeResult && (
                  <div className="mt-2 text-xs text-green-700 bg-green-50 rounded p-2">
                    ✅ Found: {scrapeResult.title || "untitled"}
                    {scrapeResult.overnight_signals.length > 0 && (
                      <span className="ml-2">🌙 Overnight signals: {scrapeResult.overnight_signals.join(", ")}</span>
                    )}
                    {scrapeResult.ages && (
                      <span className="ml-2">Ages: {scrapeResult.ages.min ?? "?"}–{scrapeResult.ages.max ?? "?"}</span>
                    )}
                    {scrapeResult.pricing && (
                      <span className="ml-2">${scrapeResult.pricing.min ?? "?"}–${scrapeResult.pricing.max ?? "?"}</span>
                    )}
                  </div>
                )}
              </form>

              <form onSubmit={handleAddCamp} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Camp Name *</label>
                  <input type="text" value={newCamp.camp_name} onChange={e => setNewCamp(f => ({ ...f, camp_name: e.target.value }))} required className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="e.g. Camp Happy Trails" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Website URL</label>
                  <input type="url" value={newCamp.website_url} onChange={e => setNewCamp(f => ({ ...f, website_url: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="https://camphappytrails.com" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">State / Region</label>
                    <input type="text" value={newCamp.region} onChange={e => setNewCamp(f => ({ ...f, region: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="ME" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                    <input type="text" value={newCamp.city} onChange={e => setNewCamp(f => ({ ...f, city: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Portland" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Do kids sleep there? 🌙</label>
                  <select value={newCamp.overnight_confirmed} onChange={e => setNewCamp(f => ({ ...f, overnight_confirmed: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400">
                    <option value="unknown">I&apos;m not sure yet</option>
                    <option value="yes">Yes! Kids sleep there</option>
                    <option value="no">No, it&apos;s a day camp</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First thoughts</label>
                  <textarea value={newCamp.notes} onChange={e => setNewCamp(f => ({ ...f, notes: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="This camp looks cool because..." rows={2} />
                </div>
                {error && <p className="text-red-500 text-sm">{error}</p>}
                <div className="flex gap-3">
                  <button type="button" onClick={() => setShowNewForm(false)} className="flex-1 border border-gray-300 py-2 rounded-lg hover:bg-gray-50">Cancel</button>
                  <button type="submit" disabled={saving} className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">{saving ? "Saving…" : "Save & Continue →"}</button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Contributions list */}
      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">
          Camps found for this mission ({contributions.length})
        </h2>
        {contributions.length === 0 ? (
          <div className="bg-white rounded-xl p-8 text-center text-gray-400">
            {user?.role === "child" ? "Click the button above to add your first camp! 🏕️" : "No contributions yet for this mission."}
          </div>
        ) : (
          <div className="space-y-2">
            {contributions.map((c) => (
              <Link key={c.id} href={`/contributions/${c.id}`} className="block bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-800">{c.camp_name}</div>
                    <div className="text-sm text-gray-400">{c.region ?? "?"} {c.city ? `• ${c.city}` : ""}</div>
                  </div>
                  <span className={`text-xs rounded-full px-3 py-1 font-medium ${statusColor[c.status]}`}>
                    {c.status.replace("_", " ")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
