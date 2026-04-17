"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { api, Mission, Contribution } from "@/lib/api";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [myContribs, setMyContribs] = useState<Contribution[]>([]);
  const [reviewQueue, setReviewQueue] = useState<Contribution[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }

    async function load() {
      try {
        const ms = await api.missions.list();
        setMissions(ms);
        if (user!.role === "child") {
          const cs = await api.contributions.list();
          setMyContribs(cs);
        } else {
          const q = await api.reviews.queue();
          setReviewQueue(q);
        }
      } finally {
        setFetching(false);
      }
    }
    load();
  }, [user, loading, router]);

  if (loading || fetching) {
    return <div className="text-gray-400 text-center mt-20">Loading…</div>;
  }

  if (!user) return null;

  return (
    <div className="space-y-8">
      <div className="bg-white rounded-2xl shadow p-6">
        <h1 className="text-2xl font-bold text-gray-800">
          {user.role === "child"
            ? `Hey ${user.display_name}! Ready to find some camps? 🏕️`
            : `Welcome back, ${user.display_name}! 👋`}
        </h1>
        <p className="text-gray-500 mt-1">
          {user.role === "child"
            ? "Pick a mission and start adding camps you find!"
            : "Review contributions from your child and manage research missions."}
        </p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard icon="🗺️" label="Active Missions" value={missions.length} href="/missions" />
        {user.role === "child" && (
          <>
            <StatCard icon="✏️" label="My Drafts" value={myContribs.filter(c => c.status === "draft").length} href="/contributions" />
            <StatCard icon="📬" label="Submitted" value={myContribs.filter(c => c.status === "submitted" || c.status === "under_review").length} href="/contributions" />
            <StatCard icon="✅" label="Approved" value={myContribs.filter(c => c.status === "approved").length} href="/contributions" />
            <StatCard icon="🔁" label="Needs Changes" value={myContribs.filter(c => c.status === "changes_requested").length} href="/contributions" />
          </>
        )}
        {user.role === "parent" && (
          <StatCard icon="📋" label="Awaiting Review" value={reviewQueue.length} href="/review" color="orange" />
        )}
      </div>

      {/* Active missions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-700">Active Missions</h2>
          <Link href="/missions" className="text-blue-600 hover:underline text-sm">See all →</Link>
        </div>
        {missions.length === 0 ? (
          <div className="bg-white rounded-xl p-6 text-center text-gray-400">
            No missions yet.{user.role === "parent" && <> <Link href="/missions/new" className="text-blue-600 hover:underline">Create one!</Link></>}
          </div>
        ) : (
          <div className="space-y-3">
            {missions.slice(0, 3).map((m) => (
              <Link key={m.id} href={`/missions/${m.id}`} className="block bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div className="font-medium text-gray-800">{m.title}</div>
                <div className="text-sm text-gray-400 mt-1">{m.description || "No description"}</div>
                <div className="flex gap-2 mt-2">
                  {m.region && <span className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5">{m.region}</span>}
                  {m.program_family && <span className="text-xs bg-green-100 text-green-700 rounded px-2 py-0.5">{m.program_family}</span>}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Parent: review queue preview */}
      {user.role === "parent" && reviewQueue.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-700">📋 Needs Your Review</h2>
            <Link href="/review" className="text-blue-600 hover:underline text-sm">See all →</Link>
          </div>
          <div className="space-y-2">
            {reviewQueue.slice(0, 3).map((c) => (
              <Link key={c.id} href={`/review/${c.id}`} className="block bg-orange-50 border border-orange-200 rounded-xl p-4 hover:bg-orange-100 transition-colors">
                <div className="font-medium text-gray-800">{c.camp_name}</div>
                <div className="text-sm text-gray-500">{c.region ?? "?"} • {c.website_url ?? "no URL"}</div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, href, color = "blue" }: {
  icon: string; label: string; value: number; href: string; color?: string;
}) {
  const colorClass = color === "orange" ? "text-orange-600" : "text-blue-600";
  return (
    <Link href={href} className="bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow text-center border border-gray-100">
      <div className="text-3xl mb-1">{icon}</div>
      <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </Link>
  );
}
