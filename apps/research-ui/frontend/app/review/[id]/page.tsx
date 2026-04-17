"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api, Contribution, Evidence, Answer, GuidedQuestion, Review } from "@/lib/api";

export default function ReviewDetailPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const cid = Number(params.id);

  const [contribution, setContribution] = useState<Contribution | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [questions, setQuestions] = useState<GuidedQuestion[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [fetching, setFetching] = useState(true);

  const [action, setAction] = useState<"approve" | "reject" | "request_changes" | "">("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [exportMsg, setExportMsg] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [c, ev, ans, qs, revs] = await Promise.all([
      api.contributions.get(cid),
      api.evidence.list(cid),
      api.answers.list(cid),
      api.answers.questions(cid),
      api.reviews.list(cid),
    ]);
    setContribution(c);
    setEvidence(ev);
    setAnswers(ans);
    setQuestions(qs);
    setReviews(revs);
  }, [cid]);

  useEffect(() => {
    if (loading) return;
    if (!user) { router.push("/login"); return; }
    if (user.role !== "parent") { router.push("/dashboard"); return; }

    let isActive = true;
    async function hydrateReview() {
      try {
        await load();
      } finally {
        if (isActive) {
          setFetching(false);
        }
      }
    }

    hydrateReview();
    return () => {
      isActive = false;
    };
  }, [user, loading, router, load]);

  async function handleReview() {
    if (!action) return;
    setSubmitting(true);
    setError("");
    try {
      await api.reviews.post(cid, action, notes);
      await load();
      setAction("");
      setNotes("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleExport() {
    try {
      const result = await api.export.promote(cid);
      setExportMsg(`✅ Exported to ${result.artifact_path}`);
    } catch (err: unknown) {
      setExportMsg(`❌ ${err instanceof Error ? err.message : "Export failed"}`);
    }
  }

  if (loading || fetching) return <div className="text-gray-400 text-center mt-20">Loading…</div>;
  if (!contribution) return <div className="text-red-400 text-center mt-20">Not found</div>;

  const answerMap: Record<string, string> = {};
  answers.forEach(a => { answerMap[a.question_key] = a.answer_text; });

  const isReviewable = contribution.status === "submitted" || contribution.status === "under_review";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/review" className="text-blue-600 hover:underline text-sm">← Review Queue</Link>
      </div>

      {/* Camp info */}
      <div className="bg-white rounded-2xl shadow p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">🏕️ {contribution.camp_name}</h1>
            <div className="flex flex-wrap gap-2 mt-2">
              {contribution.country && <Tag color="gray">{contribution.country}</Tag>}
              {contribution.region && <Tag color="blue">{contribution.region}</Tag>}
              {contribution.city && <Tag color="gray">{contribution.city}</Tag>}
              {contribution.overnight_confirmed && <Tag color={contribution.overnight_confirmed === "yes" ? "green" : "gray"}>overnight: {contribution.overnight_confirmed}</Tag>}
            </div>
          </div>
          <span className={`text-sm rounded-full px-3 py-1 font-medium ${
            { submitted: "bg-blue-100 text-blue-700", under_review: "bg-purple-100 text-purple-700", approved: "bg-green-100 text-green-700", rejected: "bg-red-100 text-red-700", changes_requested: "bg-yellow-100 text-yellow-700", draft: "bg-gray-100 text-gray-700" }[contribution.status]
          }`}>
            {contribution.status.replace("_", " ")}
          </span>
        </div>
        {contribution.website_url && (
          <a href={contribution.website_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm mt-2 block">
            {contribution.website_url}
          </a>
        )}
        {contribution.notes && <p className="text-sm text-gray-500 italic mt-2">{contribution.notes}</p>}
        {contribution.submitted_at && (
          <p className="text-xs text-gray-400 mt-2">Submitted: {new Date(contribution.submitted_at).toLocaleString()}</p>
        )}
      </div>

      {/* Answers */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">🔍 Child&apos;s Research Answers</h2>
        <div className="space-y-4">
          {questions.map((q) => (
            <div key={q.key}>
              <div className="text-sm font-medium text-gray-600">{q.label}</div>
              <div className="mt-1 bg-gray-50 rounded-lg p-3 text-sm text-gray-800">
                {answerMap[q.key] || <span className="text-gray-400 italic">Not answered</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Evidence */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">📎 Evidence ({evidence.length})</h2>
        {evidence.length === 0 ? (
          <p className="text-gray-400 text-sm">No evidence snippets added.</p>
        ) : (
          <div className="space-y-3">
            {evidence.map((ev) => (
              <div key={ev.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                {ev.url && <a href={ev.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 text-xs hover:underline break-all block mb-1">{ev.url}</a>}
                <p className="text-sm text-gray-700 italic">&ldquo;{ev.snippet}&rdquo;</p>
                {ev.capture_notes && <p className="text-xs text-gray-400 mt-1">{ev.capture_notes}</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Past reviews */}
      {reviews.length > 0 && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">📝 Review History</h2>
          <div className="space-y-2">
            {reviews.map((r) => (
              <div key={r.id} className="flex gap-3 items-start">
                <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${
                  { approve: "bg-green-100 text-green-700", reject: "bg-red-100 text-red-700", request_changes: "bg-yellow-100 text-yellow-700" }[r.action]
                }`}>{r.action.replace("_", " ")}</span>
                <div>
                  <p className="text-sm text-gray-700">{r.notes || <span className="italic text-gray-400">No notes</span>}</p>
                  <p className="text-xs text-gray-400">{new Date(r.created_at).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review action */}
      {isReviewable && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Your Decision</h2>
          <div className="flex gap-3 mb-4">
            <ActionBtn active={action === "approve"} color="green" onClick={() => setAction("approve")}>✅ Approve</ActionBtn>
            <ActionBtn active={action === "request_changes"} color="yellow" onClick={() => setAction("request_changes")}>🔁 Request Changes</ActionBtn>
            <ActionBtn active={action === "reject"} color="red" onClick={() => setAction("reject")}>❌ Reject</ActionBtn>
          </div>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            rows={3}
            placeholder="Notes for the child (optional for approve, recommended for changes/reject)…"
          />
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          <button
            onClick={handleReview}
            disabled={!action || submitting}
            className="mt-4 w-full bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit Review"}
          </button>
        </div>
      )}

      {/* Export */}
      {contribution.status === "approved" && (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center">
          <p className="font-medium text-green-800 mb-3">✅ This contribution is approved! Promote it to the staging pipeline.</p>
          <button onClick={handleExport} className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700">
            📦 Promote to Staging
          </button>
          {exportMsg && <p className="text-sm mt-3 text-gray-600">{exportMsg}</p>}
        </div>
      )}
    </div>
  );
}

function Tag({ children, color }: { children: React.ReactNode; color: string }) {
  const cls: Record<string, string> = { gray: "bg-gray-100 text-gray-600", blue: "bg-blue-100 text-blue-700", green: "bg-green-100 text-green-700" };
  return <span className={`text-xs rounded px-2 py-0.5 ${cls[color] ?? cls.gray}`}>{children}</span>;
}

function ActionBtn({ children, active, color, onClick }: {
  children: React.ReactNode; active: boolean; color: string; onClick: () => void;
}) {
  const base = "flex-1 py-2 rounded-lg text-sm font-medium border-2 transition-colors";
  const colors: Record<string, string> = {
    green: active ? "border-green-500 bg-green-50 text-green-700" : "border-gray-200 hover:border-green-300",
    yellow: active ? "border-yellow-500 bg-yellow-50 text-yellow-700" : "border-gray-200 hover:border-yellow-300",
    red: active ? "border-red-500 bg-red-50 text-red-700" : "border-gray-200 hover:border-red-300",
  };
  return <button onClick={onClick} className={`${base} ${colors[color]}`}>{children}</button>;
}
