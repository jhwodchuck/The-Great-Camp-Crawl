"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api, Contribution, Evidence, GuidedQuestion } from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  draft: "✏️ Draft",
  submitted: "📬 Submitted for Review",
  under_review: "🔍 Under Review",
  changes_requested: "🔁 Changes Requested",
  approved: "✅ Approved",
  rejected: "❌ Rejected",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  under_review: "bg-purple-100 text-purple-700",
  changes_requested: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
};

export default function ContributionDetailPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const cid = Number(params.id);

  const [contribution, setContribution] = useState<Contribution | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [questions, setQuestions] = useState<GuidedQuestion[]>([]);
  const [fetching, setFetching] = useState(true);

  // Evidence form
  const [evUrl, setEvUrl] = useState("");
  const [evSnippet, setEvSnippet] = useState("");
  const [evNotes, setEvNotes] = useState("");
  const [evSaving, setEvSaving] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const [error, setError] = useState("");

  const isEditable = contribution?.status === "draft" || contribution?.status === "changes_requested";
  const isMyContrib = user && contribution && contribution.contributor_id === user.id;
  const canEdit = isEditable && (user?.role === "parent" || isMyContrib);

  const load = useCallback(async () => {
    const [c, ev, ans, qs] = await Promise.all([
      api.contributions.get(cid),
      api.evidence.list(cid),
      api.answers.list(cid),
      api.answers.questions(cid),
    ]);
    setContribution(c);
    setEvidence(ev);
    const ansMap: Record<string, string> = {};
    ans.forEach(a => { ansMap[a.question_key] = a.answer_text; });
    setAnswers(ansMap);
    setQuestions(qs);
  }, [cid]);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }

    let isActive = true;
    async function hydrateContribution() {
      try {
        await load();
      } finally {
        if (isActive) {
          setFetching(false);
        }
      }
    }

    hydrateContribution();
    return () => {
      isActive = false;
    };
  }, [user, loading, router, load]);

  async function handleSaveAnswers() {
    setSaveStatus("saving…");
    try {
      await api.answers.upsert(cid, Object.entries(answers).map(([question_key, answer_text]) => ({ question_key, answer_text })));
      setSaveStatus("✅ Saved!");
      setTimeout(() => setSaveStatus(""), 2000);
    } catch {
      setSaveStatus("❌ Save failed");
    }
  }

  async function handleAddEvidence(e: React.FormEvent) {
    e.preventDefault();
    setEvSaving(true);
    try {
      const ev = await api.evidence.add(cid, { url: evUrl || undefined, snippet: evSnippet, capture_notes: evNotes || undefined });
      setEvidence(prev => [...prev, ev]);
      setEvUrl(""); setEvSnippet(""); setEvNotes("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add evidence");
    } finally {
      setEvSaving(false);
    }
  }

  async function handleDeleteEvidence(evId: number) {
    await api.evidence.delete(cid, evId);
    setEvidence(prev => prev.filter(e => e.id !== evId));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      await handleSaveAnswers();
      const c = await api.contributions.submit(cid);
      setContribution(c);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || fetching) return <div className="text-gray-400 text-center mt-20">Loading…</div>;
  if (!contribution) return <div className="text-red-400 text-center mt-20">Contribution not found</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link href={`/missions/${contribution.mission_id}`} className="text-blue-600 hover:underline text-sm">← Back to Mission</Link>
        <span className={`text-sm rounded-full px-3 py-1 font-medium ${STATUS_COLORS[contribution.status]}`}>
          {STATUS_LABELS[contribution.status]}
        </span>
      </div>

      {/* Camp info */}
      <div className="bg-white rounded-2xl shadow p-6 space-y-4">
        <h1 className="text-2xl font-bold text-gray-800">🏕️ {contribution.camp_name}</h1>
        {contribution.website_url && (
          <a href={contribution.website_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm break-all">
            {contribution.website_url}
          </a>
        )}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-gray-600">
          {contribution.country && <div><span className="font-medium">Country:</span> {contribution.country}</div>}
          {contribution.region && <div><span className="font-medium">Region:</span> {contribution.region}</div>}
          {contribution.city && <div><span className="font-medium">City:</span> {contribution.city}</div>}
          {contribution.overnight_confirmed && <div><span className="font-medium">Overnight:</span> {contribution.overnight_confirmed}</div>}
        </div>
        {contribution.notes && <p className="text-sm text-gray-500 italic">{contribution.notes}</p>}
      </div>

      {/* Changes requested message */}
      {contribution.status === "changes_requested" && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <p className="font-medium text-yellow-800">🔁 Your parent has requested some changes. Please update your research below and resubmit!</p>
        </div>
      )}

      {/* Guided Questions */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">🔍 Research Questions</h2>
        <div className="space-y-5">
          {questions.map((q) => (
            <div key={q.key}>
              <label className="block font-medium text-gray-700 mb-1">{q.label}</label>
              <p className="text-xs text-gray-400 mb-2">💡 {q.hint}</p>
              <textarea
                value={answers[q.key] ?? ""}
                onChange={(e) => setAnswers(prev => ({ ...prev, [q.key]: e.target.value }))}
                disabled={!canEdit}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50 disabled:text-gray-400"
                rows={2}
                placeholder={canEdit ? "Your answer…" : ""}
              />
            </div>
          ))}
        </div>
        {canEdit && (
          <div className="flex items-center gap-4 mt-4">
            <button onClick={handleSaveAnswers} className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium">
              💾 Save Draft
            </button>
            {saveStatus && <span className="text-sm text-gray-500">{saveStatus}</span>}
          </div>
        )}
      </div>

      {/* Evidence */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">📎 Evidence Snippets ({evidence.length})</h2>
        <div className="space-y-3 mb-4">
          {evidence.map((ev) => (
            <div key={ev.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              {ev.url && <a href={ev.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 text-xs hover:underline break-all block mb-1">{ev.url}</a>}
              <p className="text-sm text-gray-700 italic">&ldquo;{ev.snippet}&rdquo;</p>
              {ev.capture_notes && <p className="text-xs text-gray-400 mt-1">{ev.capture_notes}</p>}
              {canEdit && (
                <button onClick={() => handleDeleteEvidence(ev.id)} className="text-red-400 hover:text-red-600 text-xs mt-2">Remove</button>
              )}
            </div>
          ))}
        </div>
        {canEdit && (
          <form onSubmit={handleAddEvidence} className="space-y-3 border-t border-gray-100 pt-4">
            <p className="text-sm font-medium text-gray-700">Paste a quote from the website:</p>
            <input type="url" value={evUrl} onChange={e => setEvUrl(e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Page URL (optional)" />
            <textarea value={evSnippet} onChange={e => setEvSnippet(e.target.value)} required className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" rows={2} placeholder="Paste the quote or snippet here…" />
            <input type="text" value={evNotes} onChange={e => setEvNotes(e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Where did you find this? (optional)" />
            <button type="submit" disabled={evSaving} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50">
              {evSaving ? "Adding…" : "+ Add Evidence"}
            </button>
          </form>
        )}
      </div>

      {/* Submit button */}
      {canEdit && isMyContrib && (
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 text-center">
          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
          <p className="text-blue-800 font-medium mb-3">Done researching? Submit for your parent to review! 🎉</p>
          <button onClick={handleSubmit} disabled={submitting} className="bg-blue-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-blue-700 disabled:opacity-50 text-lg">
            {submitting ? "Submitting…" : "Submit for Review 📬"}
          </button>
        </div>
      )}
    </div>
  );
}
