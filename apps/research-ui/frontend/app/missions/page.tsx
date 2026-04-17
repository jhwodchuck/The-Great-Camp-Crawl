"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { api, Mission } from "@/lib/api";

export default function MissionsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }
    api.missions.list().then(setMissions).finally(() => setFetching(false));
  }, [user, loading, router]);

  if (loading || fetching) return <div className="text-gray-400 text-center mt-20">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">🗺️ Missions</h1>
        {user?.role === "parent" && (
          <Link href="/missions/new" className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium">
            + New Mission
          </Link>
        )}
      </div>

      {missions.length === 0 ? (
        <div className="bg-white rounded-xl p-12 text-center text-gray-400">
          <div className="text-5xl mb-4">🗺️</div>
          <p>No missions yet.</p>
          {user?.role === "parent" && (
            <Link href="/missions/new" className="mt-4 inline-block text-blue-600 hover:underline">
              Create the first mission
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {missions.map((m) => (
            <Link key={m.id} href={`/missions/${m.id}`}
              className="block bg-white rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow border border-gray-100">
              <div className="font-semibold text-gray-800 text-lg">{m.title}</div>
              {m.description && <div className="text-gray-500 text-sm mt-1">{m.description}</div>}
              <div className="flex flex-wrap gap-2 mt-3">
                {m.country && <Tag color="gray">{m.country}</Tag>}
                {m.region && <Tag color="blue">{m.region}</Tag>}
                {m.program_family && <Tag color="green">{m.program_family}</Tag>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Tag({ children, color }: { children: React.ReactNode; color: string }) {
  const cls = {
    gray: "bg-gray-100 text-gray-600",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
  }[color] ?? "bg-gray-100 text-gray-600";
  return <span className={`text-xs rounded px-2 py-0.5 ${cls}`}>{children}</span>;
}
