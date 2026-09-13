"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, SummerPlan } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

export default function PlansPage() {
  useRequireAuth();
  const [plans, setPlans] = useState<SummerPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    api.plans.list().then(setPlans).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.plans.create({ title, year, description });
      setShowCreate(false);
      setTitle("");
      setDescription("");
      load();
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="text-gray-400 text-center mt-20">Loading...</div>;

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">🏕️ Summer Plans</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
        >
          + New Plan
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-50 dark:bg-gray-800 p-4 rounded mb-6 space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Summer 2026"
              required
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Year</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              required
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm"
          >
            {creating ? "Creating..." : "Create Plan"}
          </button>
        </form>
      )}

      {plans.length === 0 ? (
        <p className="text-gray-500">No summer plans yet. Create one to start building your shortlist!</p>
      ) : (
        <div className="space-y-3">
          {plans.map((plan) => (
            <Link
              key={plan.id}
              href={`/plans/${plan.id}`}
              className="block bg-white dark:bg-gray-800 border rounded-lg p-4 hover:shadow-md transition"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{plan.title}</h2>
                <span className="text-sm text-gray-500">{plan.year}</span>
              </div>
              {plan.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{plan.description}</p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
