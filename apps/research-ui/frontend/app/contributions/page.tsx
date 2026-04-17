"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api, Contribution } from "@/lib/api";

export default function ContributionsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }
    api.contributions.list().then(setContributions).finally(() => setFetching(false));
  }, [user, loading, router]);

  if (loading || fetching) return <div className="text-gray-400 text-center mt-20">Loading…</div>;

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
      <h1 className="text-2xl font-bold text-gray-800">My Camp Contributions</h1>
      {contributions.length === 0 ? (
        <div className="bg-white rounded-xl p-12 text-center text-gray-400">
          <div className="text-5xl mb-4">🏕️</div>
          <p>You haven&apos;t added any camps yet.</p>
          <Link href="/missions" className="mt-4 inline-block text-blue-600 hover:underline">Browse missions to get started!</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {contributions.map((c) => (
            <Link key={c.id} href={`/contributions/${c.id}`} className="block bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-800">{c.camp_name}</div>
                  <div className="text-sm text-gray-400 mt-0.5">
                    {c.region ?? "?"} {c.city ? `· ${c.city}` : ""}
                    {c.website_url && ` · ${c.website_url}`}
                  </div>
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
  );
}
