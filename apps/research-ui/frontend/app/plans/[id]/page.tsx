"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, SummerPlan, ShortlistItem, ShortlistStatus, ResearchClipboard } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

const STATUS_LABELS: Record<ShortlistStatus, string> = {
  interested: "🤔 Interested",
  researching: "🔍 Researching",
  applied: "📝 Applied",
  going: "✅ Going",
  passed: "⏭️ Passed",
};
const STATUS_COLORS: Record<ShortlistStatus, string> = {
  interested: "bg-yellow-100 text-yellow-800",
  researching: "bg-blue-100 text-blue-800",
  applied: "bg-purple-100 text-purple-800",
  going: "bg-green-100 text-green-800",
  passed: "bg-gray-100 text-gray-500",
};

export default function PlanDetailPage() {
  useRequireAuth();
  const params = useParams();
  const planId = Number(params.id);
  const [plan, setPlan] = useState<SummerPlan | null>(null);
  const [items, setItems] = useState<ShortlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [noteText, setNoteText] = useState("");
  const [noteUrl, setNoteUrl] = useState("");
  const [clipboardData, setClipboardData] = useState<ResearchClipboard | null>(null);
  const [showClipboard, setShowClipboard] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [importResult, setImportResult] = useState("");
  const [showPaste, setShowPaste] = useState(false);

  const load = useCallback(async () => {
    const [p, sl] = await Promise.all([
      api.plans.get(planId),
      api.plans.shortlist(planId),
    ]);
    setPlan(p);
    setItems(sl);
    setLoading(false);
  }, [planId]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      api.plans.get(planId),
      api.plans.shortlist(planId),
    ]).then(([nextPlan, nextItems]) => {
      if (cancelled) return;
      setPlan(nextPlan);
      setItems(nextItems);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [planId]);

  async function handleStatusChange(itemId: number, status: ShortlistStatus) {
    await api.plans.updateItem(itemId, { status });
    load();
  }

  async function handleRemove(itemId: number) {
    if (!confirm("Remove from shortlist?")) return;
    await api.plans.removeItem(itemId);
    load();
  }

  async function handleAddNote(itemId: number) {
    if (!noteText.trim()) return;
    await api.plans.addNote(itemId, noteText, noteUrl || undefined);
    setNoteText("");
    setNoteUrl("");
    load();
  }

  async function handleDeleteNote(noteId: number) {
    await api.plans.deleteNote(noteId);
    load();
  }

  async function handleCopyClipboard() {
    const data = await api.plans.clipboard(planId);
    setClipboardData(data);
    setShowClipboard(true);
    const text = buildPromptText(data);
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  function buildPromptText(data: ResearchClipboard): string {
    const lines: string[] = [
      `I'm researching summer camps/programs for "${data.plan_title}". Below is my current shortlist. For each one, please research and respond with a JSON object I can paste back.`,
      "",
      "For each camp, I'd like:",
      "- A 2-3 sentence summary of the program",
      "- Key details: application deadlines, selectivity, what participants do",
      "- Any red flags or things to watch out for",
      "- Your overall recommendation (strong yes / yes / maybe / skip) and why",
      "",
      "Please respond as JSON in this exact format:",
      '```json',
      '{ "items": [',
      '  { "name": "Camp Name Exactly As Listed", "notes": "Your research findings here..." }',
      '] }',
      '```',
      "",
      "Here is my shortlist:",
      "",
      JSON.stringify(data.items, null, 2),
    ];
    return lines.join("\n");
  }

  async function handleImportResearch() {
    try {
      const parsed = JSON.parse(pasteText);
      const result = await api.plans.importResearch(planId, parsed.items || parsed);
      setImportResult(`Imported ${result.imported} of ${result.total_in_payload} items`);
      setPasteText("");
      setShowPaste(false);
      load();
    } catch (e) {
      setImportResult(`Error: ${e instanceof Error ? e.message : "Invalid JSON"}`);
    }
  }

  if (loading) return <div className="text-gray-400 text-center mt-20">Loading...</div>;
  if (!plan) return <div className="text-red-400 text-center mt-20">Plan not found</div>;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <Link href="/plans" className="text-blue-600 text-sm hover:underline mb-4 block">
        ← All Plans
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{plan.title}</h1>
          {plan.description && <p className="text-gray-500 mt-1">{plan.description}</p>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopyClipboard}
            className="bg-purple-600 text-white px-3 py-2 rounded text-sm hover:bg-purple-700"
          >
            {copied ? "✅ Copied!" : "📋 Copy for ChatGPT"}
          </button>
          <button
            onClick={() => setShowPaste(!showPaste)}
            className="bg-indigo-600 text-white px-3 py-2 rounded text-sm hover:bg-indigo-700"
          >
            📥 Paste Research
          </button>
        </div>
      </div>

      {/* ── ChatGPT Clipboard Section ── */}
      {showClipboard && clipboardData && (
        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-purple-800 dark:text-purple-200">
              📋 ChatGPT Research Prompt
            </h2>
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  await navigator.clipboard.writeText(buildPromptText(clipboardData));
                  setCopied(true);
                  setTimeout(() => setCopied(false), 3000);
                }}
                className="text-xs bg-purple-600 text-white px-3 py-1 rounded hover:bg-purple-700"
              >
                {copied ? "✅ Copied!" : "Copy Again"}
              </button>
              <button
                onClick={() => { setShowClipboard(false); setClipboardData(null); }}
                className="text-xs text-purple-500 hover:text-purple-700 px-2"
              >
                ✕ Close
              </button>
            </div>
          </div>

          <p className="text-xs text-purple-700 dark:text-purple-300 mb-3">
            This prompt has been copied to your clipboard. Paste it into ChatGPT, then paste the response back using &quot;Paste Research&quot; above.
          </p>

          {/* Summary of what's being sent */}
          <div className="mb-3 text-sm text-purple-900 dark:text-purple-100">
            <span className="font-medium">{clipboardData.items.length} camp{clipboardData.items.length !== 1 ? "s" : ""}</span> included:
          </div>
          <div className="grid gap-2 mb-4">
            {clipboardData.items.map((item, i) => {
              const name = item.name as string | undefined;
              const status = item.status as string | undefined;
              const location = item.location as string | undefined;
              const ages = item.ages as string | undefined;
              const pricing = item.pricing as string | undefined;
              const durationDays = item.duration_days as string | undefined;
              const ourNotes = item.our_notes as string[] | undefined;

              return (
                <div key={i} className="bg-white dark:bg-gray-800 rounded px-3 py-2 text-sm border border-purple-100 dark:border-purple-800">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{name}</span>
                    <span className="text-xs text-gray-500">{status}</span>
                  </div>
                  {location && (
                    <span className="text-xs text-gray-500">{location}</span>
                  )}
                  <div className="flex gap-3 text-xs text-gray-400 mt-0.5">
                    {ages && <span>Ages {ages}</span>}
                    {pricing && <span>{pricing}</span>}
                    {durationDays && <span>{durationDays} days</span>}
                  </div>
                  {ourNotes && (
                    <div className="text-xs text-gray-500 mt-1 italic">
                      Notes: {ourNotes.join(" · ")}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Raw prompt preview */}
          <details className="text-xs">
            <summary className="cursor-pointer text-purple-600 dark:text-purple-400 hover:underline">
              Show raw prompt text
            </summary>
            <pre className="mt-2 bg-white dark:bg-gray-900 border rounded p-3 overflow-x-auto whitespace-pre-wrap text-gray-700 dark:text-gray-300 max-h-64 overflow-y-auto">
              {buildPromptText(clipboardData)}
            </pre>
          </details>
        </div>
      )}

      {/* ── Paste Research Section ── */}
      {showPaste && (
        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-indigo-800 dark:text-indigo-200">
              📥 Import Research from ChatGPT
            </h2>
            <button
              onClick={() => { setShowPaste(false); setImportResult(""); }}
              className="text-xs text-indigo-500 hover:text-indigo-700 px-2"
            >
              ✕ Close
            </button>
          </div>
          <p className="text-xs text-indigo-700 dark:text-indigo-300 mb-3">
            Paste ChatGPT&apos;s JSON response below. Notes will be matched to your shortlist by camp name.
          </p>
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            rows={10}
            placeholder={'{\n  "items": [\n    { "name": "Camp Name", "notes": "Research findings..." }\n  ]\n}'}
            className="w-full border border-indigo-200 dark:border-indigo-700 rounded px-3 py-2 text-sm font-mono dark:bg-gray-800 mb-3"
          />
          <div className="flex items-center gap-3">
            <button
              onClick={handleImportResearch}
              disabled={!pasteText.trim()}
              className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50"
            >
              Import Notes
            </button>
            {importResult && (
              <span className={`text-sm ${importResult.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>
                {importResult}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Add camp link */}
      <div className="mb-4">
        <Link
          href={`/camps?addToPlan=${planId}`}
          className="text-blue-600 text-sm hover:underline"
        >
          + Browse catalog to add camps
        </Link>
      </div>

      {/* Shortlist */}
      {items.length === 0 ? (
        <p className="text-gray-500">No camps on this shortlist yet. Browse the catalog to add some!</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const campName = item.camp?.name || item.custom_camp_name || "Unknown";
            const isExpanded = expandedItem === item.id;

            return (
              <div key={item.id} className="bg-white dark:bg-gray-800 border rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {isExpanded ? "▼" : "▶"}
                      </button>
                      {item.camp ? (
                        <Link
                          href={`/camps/${item.camp.record_id}`}
                          className="font-semibold text-blue-600 hover:underline"
                        >
                          {campName}
                        </Link>
                      ) : (
                        <span className="font-semibold">{campName}</span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[item.status]}`}>
                        {STATUS_LABELS[item.status]}
                      </span>
                    </div>
                    {item.camp && (
                      <div className="text-xs text-gray-500 ml-6 mt-1">
                        {[item.camp.city, item.camp.region, item.camp.country].filter(Boolean).join(", ")}
                        {item.camp.ages_min || item.camp.ages_max
                          ? ` · Ages ${item.camp.ages_min ?? "?"}-${item.camp.ages_max ?? "?"}`
                          : ""}
                        {item.camp.pricing_min || item.camp.pricing_max
                          ? ` · $${item.camp.pricing_min ?? "?"}–$${item.camp.pricing_max ?? "?"}`
                          : ""}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <select
                      value={item.status}
                      onChange={(e) => handleStatusChange(item.id, e.target.value as ShortlistStatus)}
                      className="text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600"
                    >
                      {Object.entries(STATUS_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>{v}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => handleRemove(item.id)}
                      className="text-red-400 hover:text-red-600 text-sm px-1"
                      title="Remove"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="mt-3 ml-6 space-y-3">
                    {/* Notes */}
                    {item.notes.length > 0 && (
                      <div className="space-y-2">
                        {item.notes.map((note) => (
                          <div key={note.id} className="bg-gray-50 dark:bg-gray-700 p-3 rounded text-sm">
                            <div className="flex justify-between text-xs text-gray-400 mb-1">
                              <span>{note.author_display_name ?? "Unknown"}</span>
                              <div className="flex gap-2">
                                <span>{new Date(note.created_at).toLocaleDateString()}</span>
                                <button
                                  onClick={() => handleDeleteNote(note.id)}
                                  className="text-red-400 hover:text-red-600"
                                >
                                  ✕
                                </button>
                              </div>
                            </div>
                            <p className="whitespace-pre-wrap">{note.body}</p>
                            {note.source_url && (
                              <a
                                href={note.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-500 text-xs hover:underline"
                              >
                                {note.source_url}
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add note form */}
                    <div className="flex gap-2">
                      <input
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="Add a note..."
                        className="flex-1 border rounded px-2 py-1 text-sm dark:bg-gray-700 dark:border-gray-600"
                      />
                      <input
                        value={noteUrl}
                        onChange={(e) => setNoteUrl(e.target.value)}
                        placeholder="Source URL (optional)"
                        className="w-48 border rounded px-2 py-1 text-sm dark:bg-gray-700 dark:border-gray-600"
                      />
                      <button
                        onClick={() => handleAddNote(item.id)}
                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                      >
                        Add
                      </button>
                    </div>
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
