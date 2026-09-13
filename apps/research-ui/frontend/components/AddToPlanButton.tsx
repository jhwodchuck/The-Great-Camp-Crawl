"use client";

import { useEffect, useState } from "react";
import { api, SummerPlan } from "@/lib/api";

export default function AddToPlanButton({ campId }: { campId: number }) {
  const [plans, setPlans] = useState<SummerPlan[]>([]);
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (open && plans.length === 0) {
      api.plans.list().then(setPlans);
    }
  }, [open, plans.length]);

  async function handleAdd(planId: number) {
    setAdding(true);
    setMessage("");
    try {
      await api.plans.addToShortlist(planId, { camp_id: campId });
      setMessage("Added!");
      setTimeout(() => { setMessage(""); setOpen(false); }, 1500);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Error");
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
      >
        + Add to Plan
      </button>
      {open && (
        <div className="absolute right-0 mt-1 bg-white dark:bg-gray-800 border rounded shadow-lg z-10 min-w-48">
          {plans.length === 0 ? (
            <div className="p-3 text-sm text-gray-500">Loading...</div>
          ) : (
            plans.map((p) => (
              <button
                key={p.id}
                onClick={() => handleAdd(p.id)}
                disabled={adding}
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                {p.title} ({p.year})
              </button>
            ))
          )}
          {message && <div className="px-4 py-2 text-xs text-green-600">{message}</div>}
        </div>
      )}
    </div>
  );
}
