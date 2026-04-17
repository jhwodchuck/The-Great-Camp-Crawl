"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api, Contribution } from "@/lib/api";

export default function ReviewQueuePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [queue, setQueue] = useState<Contribution[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }
    if (user.role !== "parent") { router.push("/dashboard"); return; }
    api.reviews.queue().then(setQueue).finally(() => setFetching(false));
  }, [user, loading, router]);

  if (loading || fetching) return <div className="text-gray-400 text-center mt-20">Loading…</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">📋 Review Queue</h1>
      <p className="text-gray-500 text-sm">{queue.length} contribution{queue.length !== 1 ? "s" : ""} awaiting review</p>

      {queue.length === 0 ? (
        <div className="bg-white rounded-xl p-12 text-center text-gray-400">
          <div className="text-5xl mb-4">🎉</div>
          <p>All caught up! No contributions pending review.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {queue.map((c) => (
            <Link key={c.id} href={`/review/${c.id}`} className="block bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow border border-orange-100 hover:border-orange-300">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-gray-800">{c.camp_name}</div>
                  <div className="text-sm text-gray-400 mt-0.5">
                    {c.region ?? "?"} {c.city ? `· ${c.city}` : ""}
                    {c.submitted_at && ` · submitted ${new Date(c.submitted_at).toLocaleDateString()}`}
                  </div>
                  {c.website_url && <div className="text-xs text-blue-500 truncate mt-1 max-w-sm">{c.website_url}</div>}
                </div>
                <span className="text-xs bg-orange-100 text-orange-700 rounded-full px-3 py-1 font-medium">
                  {c.status.replace("_", " ")}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
