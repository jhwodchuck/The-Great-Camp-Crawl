"use client";

import { useEffect, useState } from "react";
import { api, Favorite } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function FavoriteButton({ campId }: { campId: number }) {
  const { user } = useAuth();
  const [fav, setFav] = useState<Favorite | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.favorites.list().then(favs => {
      const match = favs.find(f => f.camp_id === campId);
      setFav(match ?? null);
    }).catch(() => {});
  }, [user, campId]);

  if (!user) return null;

  async function toggle() {
    setBusy(true);
    try {
      if (fav) {
        await api.favorites.remove(campId);
        setFav(null);
      } else {
        const newFav = await api.favorites.add(campId);
        setFav(newFav);
      }
    } catch (err) {
      console.error("Favorite toggle failed", err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={busy}
      className={`text-2xl transition-transform hover:scale-110 disabled:opacity-50 ${
        fav ? "text-red-500" : "text-gray-300 hover:text-red-400"
      }`}
      title={fav ? "Remove from favorites" : "Add to favorites"}
    >
      {fav ? "❤️" : "🤍"}
    </button>
  );
}
