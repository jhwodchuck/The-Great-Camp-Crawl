"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import Link from "next/link";

export default function NewMissionPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ title: "", description: "", region: "", country: "US", program_family: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  if (!loading && !user) {
    router.push("/login");
    return null;
  }

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const mission = await api.missions.create({
        title: form.title,
        description: form.description,
        region: form.region || undefined,
        country: form.country || undefined,
        program_family: form.program_family || undefined,
      });
      router.push(`/missions/${mission.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create mission");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/missions" className="text-blue-600 hover:underline text-sm">← Missions</Link>
        <h1 className="text-xl font-bold text-gray-800">Create New Mission</h1>
      </div>

      <div className="bg-white rounded-2xl shadow p-6 text-gray-900">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mission Title *</label>
            <p className="text-xs text-gray-400 mb-1">What are we looking for?</p>
            <input
              type="text"
              value={form.title}
              onChange={(e) => update("title", e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="e.g. Find Arts Camps in New England"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <p className="text-xs text-gray-400 mb-1">Give your child some context</p>
            <textarea
              value={form.description}
              onChange={(e) => update("description", e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 min-h-[80px]"
              placeholder="We're looking for overnight arts camps for ages 10-14..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
              <input type="text" value={form.country} onChange={(e) => update("country", e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="US" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Region / State</label>
              <input type="text" value={form.region} onChange={(e) => update("region", e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="ME, VT, NY…" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Program Family</label>
            <input type="text" value={form.program_family} onChange={(e) => update("program_family", e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="arts-camps, stem, music…" />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={saving} className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Creating…" : "Create Mission"}
          </button>
        </form>
      </div>
    </div>
  );
}
