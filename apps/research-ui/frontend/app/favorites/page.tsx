"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
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

export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/"); return; }
    api.favorites.list()
      .then(setFavorites)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user, authLoading, router]);

  async function handleRemove(campId: number) {
    await api.favorites.remove(campId);
    setFavorites(f => f.filter(fav => fav.camp_id !== campId));
    setSelected(s => { const n = new Set(s); n.delete(campId); return n; });
  }

  async function handleSaveNotes(campId: number) {
    const updated = await api.favorites.update(campId, editNotes);
    setFavorites(f => f.map(fav => fav.camp_id === campId ? updated : fav));
    setEditingId(null);
  }

  function toggleSelect(campId: number) {
    setSelected(s => {
      const n = new Set(s);
      if (n.has(campId)) n.delete(campId);
      else if (n.size < 4) n.add(campId);
      return n;
    });
  }

  if (authLoading || loading) return <div className="text-gray-400 text-center mt-20">Loading...</div>;
  if (!user) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">❤️ My Favorites</h1>
        {selected.size >= 2 && (
          <Link
            href={`/compare?ids=${Array.from(selected).join(",")}`}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Compare {selected.size} camps →
          </Link>
        )}
      </div>

      {favorites.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg mb-2">No favorites yet!</p>
          <Link href="/camps" className="text-blue-600 hover:underline">Browse the catalog →</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {favorites.map(fav => {
            const camp = fav.camp;
            const families = parseJsonArray(camp.program_family);
            const isEditing = editingId === fav.camp_id;

            return (
              <div key={fav.id} className="bg-white rounded-xl shadow p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selected.has(fav.camp_id)}
                    onChange={() => toggleSelect(fav.camp_id)}
                    className="mt-1.5 rounded"
                    title="Select for comparison"
                  />
                  <div className="flex-1">
                    <Link
                      href={`/camps/${encodeURIComponent(camp.record_id)}`}
                      className="font-bold text-gray-800 hover:text-blue-600 text-base"
                    >
                      {camp.display_name || camp.name}
                    </Link>
                    <p className="text-sm text-gray-500">
                      {[camp.city, camp.region, camp.country].filter(Boolean).join(", ")}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-1 text-xs text-gray-600">
                      {(camp.ages_min || camp.ages_max) && (
                        <span className="bg-blue-50 px-2 py-0.5 rounded">Ages {camp.ages_min ?? "?"}–{camp.ages_max ?? "?"}</span>
                      )}
                      {(camp.pricing_min || camp.pricing_max) && (
                        <span className="bg-yellow-50 px-2 py-0.5 rounded">${camp.pricing_min ?? "?"}–${camp.pricing_max ?? "?"}</span>
                      )}
                      {camp.overnight_confirmed && (
                        <span className="bg-green-50 text-green-700 px-2 py-0.5 rounded">🌙 Overnight</span>
                      )}
                      {families.slice(0, 2).map(f => (
                        <span key={f} className="bg-gray-100 px-2 py-0.5 rounded">{formatProgramFamily(f)}</span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(fav.camp_id)}
                    className="text-red-400 hover:text-red-600 text-sm"
                    title="Remove from favorites"
                  >
                    ✕
                  </button>
                </div>

                {/* Notes */}
                {isEditing ? (
                  <div className="pl-8 space-y-2">
                    <textarea
                      value={editNotes}
                      onChange={e => setEditNotes(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                      rows={3}
                      placeholder="Your pros, cons, and notes..."
                    />
                    <div className="flex gap-2">
                      <button onClick={() => handleSaveNotes(fav.camp_id)} className="bg-blue-600 text-white px-3 py-1 rounded text-sm">Save</button>
                      <button onClick={() => setEditingId(null)} className="text-gray-500 text-sm">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="pl-8">
                    {fav.notes ? (
                      <p className="text-sm text-gray-600 italic">{fav.notes}</p>
                    ) : null}
                    <button
                      onClick={() => { setEditingId(fav.camp_id); setEditNotes(fav.notes ?? ""); }}
                      className="text-blue-600 hover:underline text-xs mt-1"
                    >
                      {fav.notes ? "Edit notes" : "+ Add pros/cons notes"}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
