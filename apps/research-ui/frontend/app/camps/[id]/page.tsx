"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, Camp, CampEnrichmentPayload, CampPlanMembership } from "@/lib/api";
import FavoriteButton from "@/components/FavoriteButton";
import AddToPlanButton from "@/components/AddToPlanButton";
import { useAuth } from "@/lib/auth";
import { buildContributionPrefillQuery } from "@/lib/contribution-prefill";

function parseJsonArray(val: string | null): string[] {
  if (!val) return [];
  try {
    const parsed = JSON.parse(val);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function formatProgramFamily(pf: string): string {
  return pf.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/** Replace literal control characters inside JSON string values with their escape sequences. */
function sanitizeJsonString(text: string): string {
  let inString = false;
  let escaped = false;
  let result = "";
  for (const char of text) {
    if (escaped) {
      result += char;
      escaped = false;
      continue;
    }
    if (char === "\\" && inString) {
      result += char;
      escaped = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      result += char;
      continue;
    }
    if (inString) {
      if (char === "\n") { result += "\\n"; continue; }
      if (char === "\r") { result += "\\r"; continue; }
      if (char === "\t") { result += "\\t"; continue; }
    }
    result += char;
  }
  return result;
}

export default function CampDetailPage() {
  const { user, loading: authLoading } = useAuth();
  const params = useParams();
  const recordId = params.id as string;
  const [camp, setCamp] = useState<Camp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [moderationReason, setModerationReason] = useState("not_a_camp");
  const [moderationNotes, setModerationNotes] = useState("");
  const [moderating, setModerating] = useState(false);
  const [actionError, setActionError] = useState("");
  const [copied, setCopied] = useState(false);
  const [copiedDeep, setCopiedDeep] = useState(false);
  const [showClipboard, setShowClipboard] = useState(false);
  const [clipboardLabel, setClipboardLabel] = useState("");
  const [clipboardText, setClipboardText] = useState("");
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [importResult, setImportResult] = useState("");
  const [campPlans, setCampPlans] = useState<CampPlanMembership[]>([]);

  useEffect(() => {
    api.camps
      .get(recordId)
      .then(setCamp)
      .catch(err => setError(err.message || "Failed to load camp"))
      .finally(() => setLoading(false));
  }, [recordId]);

  useEffect(() => {
    if (!authLoading && user) {
      api.camps.plans(recordId).then(setCampPlans).catch(() => {});
    }
  }, [recordId, user, authLoading]);

  if (loading) return <div className="text-gray-400 text-center mt-20">Loading...</div>;
  if (error) return <div className="text-red-400 text-center mt-20">{error}</div>;
  if (!camp) return <div className="text-gray-400 text-center mt-20">Camp not found</div>;

  const families = parseJsonArray(camp.program_family);
  const types = parseJsonArray(camp.camp_types);
  const contributionQuery = buildContributionPrefillQuery({
    recordId: camp.record_id,
    campName: camp.display_name || camp.name,
    websiteUrl: camp.website_url || undefined,
    country: camp.country || undefined,
    region: camp.region || undefined,
    city: camp.city || undefined,
    venueName: camp.venue_name || undefined,
  });
  const contributionHref = contributionQuery ? `/missions?${contributionQuery}` : "/missions";

  async function handleModeration(isExcluded: boolean) {
    setModerating(true);
    setActionError("");
    try {
      const updated = await api.camps.moderate(recordId, {
        is_excluded: isExcluded,
        reason: isExcluded ? moderationReason : undefined,
        notes: isExcluded ? moderationNotes : undefined,
      });
      setCamp(updated);
      if (!isExcluded) {
        setModerationNotes("");
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to update camp moderation");
    } finally {
      setModerating(false);
    }
  }

  function isUnknownLocation(val: string | null | undefined): boolean {
    if (!val) return true;
    return ["unknown", "unkn", "n/a", ""].includes(val.trim().toLowerCase());
  }

  function buildCampPrompt(c: Camp): string {
    const missing: string[] = [];
    if (isUnknownLocation(c.city)) missing.push("city where the program is physically located (city)");
    if (isUnknownLocation(c.region)) missing.push("state/province/region code, e.g. TX or BC (region)");
    if (c.ages_min == null && c.ages_max == null) missing.push("age range (ages_min, ages_max)");
    if (c.grades_min == null && c.grades_max == null) missing.push("grade range (grades_min, grades_max)");
    if (c.duration_min_days == null && c.duration_max_days == null) missing.push("session duration in days (duration_min_days, duration_max_days)");
    if (c.pricing_min == null && c.pricing_max == null) missing.push("pricing range in USD (pricing_min, pricing_max, pricing_currency)");
    if (c.contact_email == null) missing.push("contact email (contact_email)");
    if (c.contact_phone == null) missing.push("contact phone (contact_phone)");
    if (c.operator_name == null) missing.push("organization/operator name (operator_name)");
    if (c.overnight_confirmed == null) missing.push("whether this is an overnight/residential program (overnight_confirmed: true/false)");
    if (c.active_confirmed == null) missing.push("whether this program is still active for 2025-2026 (active_confirmed: true/false)");
    if (c.boarding_included == null) missing.push("whether boarding/housing is included in the price (boarding_included: true/false)");
    if (c.description_md == null || c.description_md.trim().length < 100) missing.push("a detailed description of the program in markdown (description_md)");

    const lines: string[] = [
      `I'm researching this youth program for my child. Please visit the website and fill in the missing details.`,
      "",
      `**Program:** ${c.display_name || c.name}`,
      `**Location:** ${[c.city, c.region, c.country].filter(Boolean).join(", ")}`,
    ];
    if (c.website_url) lines.push(`**Website:** ${c.website_url}`);
    if (c.operator_name) lines.push(`**Operator:** ${c.operator_name}`);

    lines.push("");
    if (missing.length > 0) {
      lines.push("**Missing information I need filled in:**");
      missing.forEach(m => lines.push(`- ${m}`));
    } else {
      lines.push("All key fields are filled. Please verify the existing data and add anything else notable.");
    }

    lines.push(
      "",
      "Please respond with ONLY a JSON object using these exact field names (omit any you can't determine):",
      "```json",
      "{",
      '  "ages_min": 10,',
      '  "ages_max": 17,',
      '  "grades_min": 5,',
      '  "grades_max": 12,',
      '  "duration_min_days": 7,',
      '  "duration_max_days": 14,',
      '  "pricing_currency": "USD",',
      '  "pricing_min": 1500,',
      '  "pricing_max": 3000,',
      '  "boarding_included": true,',
      '  "overnight_confirmed": true,',
      '  "active_confirmed": true,',
      '  "contact_email": "info@example.com",',
      '  "contact_phone": "555-123-4567",',
      '  "operator_name": "Organization Name",',
      '  "city": "Austin",',
      '  "region": "TX",',
      '  "description_md": "A 2-3 paragraph markdown description of the program..."',
      "}",
      "```",
    );

    return lines.join("\n");
  }

  function buildDeepResearchPrompt(c: Camp): string {
    const lines: string[] = [
      `I'm a parent researching residential/overnight youth programs for my child. Please do a **thorough deep-dive** on the program below — browse every relevant page (home, about, programs, admissions, FAQ, housing, cost, staff, alumni, contact) and compile everything a parent would want to know before applying. The goal is a reference document so complete that I never need to visit the site myself.`,
      "",
      `**Program:** ${c.display_name || c.name}`,
      `**Location:** ${[c.city, c.region, c.country].filter(Boolean).join(", ") || "Unknown"}`,
    ];
    if (c.website_url) lines.push(`**Website:** ${c.website_url}`);
    if (c.operator_name) lines.push(`**Operator:** ${c.operator_name}`);

    lines.push(
      "",
      "---",
      "",
      "## What to research and include",
      "",
      "**Program basics**",
      "- Full official name, operator/host organization, and physical address of venue",
      "- Is this genuinely overnight/residential, or day-only? (confirm clearly)",
      "- Is the program currently active and accepting applications for 2025 or 2026?",
      "- Age range, grade range, and any eligibility prerequisites",
      "",
      "**Session structure**",
      "- All available session lengths (e.g. 1-week, 2-week, full summer)",
      "- Specific session dates or date windows for the upcoming year",
      "- Typical daily schedule — wake-up through lights-out",
      "- How many participants per session; cohort size",
      "",
      "**Curriculum & activities**",
      "- What participants actually do each day: classes, projects, field work, performances, competitions, labs, etc.",
      "- Instructors: credentials, whether they are professors, industry professionals, or counselors",
      "- Academic rigor level — casual enrichment vs. rigorous coursework vs. somewhere in between",
      "- Any certifications, portfolios, or tangible outputs participants leave with",
      "",
      "**Admissions & selectivity**",
      "- Is it selective (application + review) or open enrollment (pay and attend)?",
      "- If selective: acceptance rate if known, what they look for, required essays/portfolio/test scores",
      "- Application open and deadline dates",
      "- Notification timeline",
      "",
      "**Cost & financial aid**",
      "- Full tuition/program fee (break down if multiple sessions or tiers)",
      "- What is included: housing, meals, materials, activities, transportation from airport, etc.",
      "- What is NOT included and typical additional costs",
      "- Scholarships, fellowships, or need-based aid available — amounts, how to apply, deadlines",
      "- Refund/cancellation policy",
      "",
      "**Housing & facilities**",
      "- Type of housing: dorms, cabins, host families, campus residence halls",
      "- Room assignments: shared or private; co-ed or separated",
      "- Meals: dining hall, dietary accommodations, quality notes if mentioned",
      "- Campus or venue description — setting (urban campus, lakeside, forest, etc.)",
      "- Key facilities: labs, studios, stages, pools, athletic fields, maker spaces",
      "",
      "**Social environment & culture**",
      "- Typical camper/participant background and where they come from (national, international, regional)",
      "- Friendships, community feel — is it competitive, collaborative, or mixed?",
      "- Evening and weekend activities, free time, social events",
      "- Technology policy: phones allowed, restricted, or confiscated?",
      "",
      "**Health, safety & supervision**",
      "- Counselor-to-participant ratio",
      "- Medical staff or clinic on-site",
      "- Any notable safety policies or accreditations (ACA accreditation, university affiliation, etc.)",
      "",
      "**Staff & leadership**",
      "- Who directs or founded the program and their background",
      "- Counselor/TA profile: undergrads, grad students, working professionals?",
      "",
      "**Outcomes & reputation**",
      "- Notable alumni outcomes, college placements, awards, or published work if known",
      "- Press mentions, rankings, or third-party endorsements",
      "- Any red flags, controversies, or common criticisms found online",
      "",
      "**Logistics for families**",
      "- Nearest major airport and whether shuttle/transport is provided",
      "- What to bring / packing list highlights",
      "- Visitation policy during session",
      "- Contact: main phone, email, admissions contact name if available",
      "",
      "---",
      "",
      "## Output format",
      "",
      "Respond with **ONLY** a valid JSON object — no prose before or after it.",
      "The `description_md` field must use rich Markdown with `##` section headers matching the topics above.",
      "Write at least 600 words in `description_md`. Do not truncate or summarize — be exhaustive.",
      "Use bullet lists, bold labels, and tables where they help readability.",
      "If you cannot find a piece of information, write `*Not found on site.*` under that section rather than skipping it.",
      "",
      "```json",
      "{",
      '  "overnight_confirmed": true,',
      '  "active_confirmed": true,',
      '  "description_md": "## Overview\\n\\n[3-4 sentence intro]\\n\\n## Session Structure\\n\\n..."',
      "}",
      "```",
    );
    return lines.join("\n");
  }

  async function handleCopyPrompt() {
    if (!camp) return;
    const text = buildCampPrompt(camp);
    await navigator.clipboard.writeText(text);
    setClipboardText(text);
    setClipboardLabel("Metadata prompt copied to clipboard:");
    setShowClipboard(true);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  async function handleCopyDeepPrompt() {
    if (!camp) return;
    const text = buildDeepResearchPrompt(camp);
    await navigator.clipboard.writeText(text);
    setClipboardText(text);
    setClipboardLabel("Deep research prompt copied to clipboard:");
    setShowClipboard(true);
    setCopiedDeep(true);
    setTimeout(() => setCopiedDeep(false), 3000);
  }

  async function handleImportEnrichment() {
    setImportResult("");
    try {
      // Strip markdown code fences if present
      let text = pasteText.trim();
      if (text.startsWith("```")) {
        text = text.replace(/^```(?:json)?\s*\n?/, "").replace(/\n?```\s*$/, "");
      }
      // Extract the first complete JSON object, discarding any trailing content
      // (e.g. ChatGPT sometimes appends markdown footnote links after the JSON block)
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) text = jsonMatch[0];
      // Fix unescaped control characters inside JSON string values (common in pasted ChatGPT output)
      text = sanitizeJsonString(text);
      const parsed = JSON.parse(text) as CampEnrichmentPayload;
      const updated = await api.camps.enrich(recordId, parsed);
      setCamp(updated);
      setImportResult("Enrichment applied successfully!");
      setPasteText("");
      setShowPaste(false);
    } catch (e) {
      setImportResult(`Error: ${e instanceof Error ? e.message : "Invalid JSON"}`);
    }
  }

  return (
    <div className="space-y-6">
      <Link href="/camps" className="text-blue-600 hover:underline text-sm">
        ← Back to Catalog
      </Link>

      {/* Header */}
      <div className="bg-white rounded-2xl shadow p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              🏕️ {camp.display_name || camp.name}
            </h1>
            <p className="text-gray-500 mt-1">
              {[camp.city, camp.region, camp.country].filter(Boolean).join(", ")}
            </p>
          </div>
          <div className="flex gap-2">
            <AddToPlanButton campId={camp.id} />
            <FavoriteButton campId={camp.id} />
          </div>
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2 mt-3">
          {camp.overnight_confirmed && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">🌙 Overnight Confirmed</span>
          )}
          {camp.active_confirmed && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">✅ Active</span>
          )}
          {camp.confidence && (
            user?.role === "parent" ? (
              <select
                value={camp.confidence}
                onChange={async e => {
                  const updated = await api.camps.enrich(recordId, { confidence: e.target.value });
                  setCamp(updated);
                }}
                className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full border-0 cursor-pointer"
              >
                <option value="low">Confidence: low</option>
                <option value="medium">Confidence: medium</option>
                <option value="high">Confidence: high</option>
              </select>
            ) : (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                Confidence: {camp.confidence}
              </span>
            )
          )}
          {camp.draft_status && (
            user?.role === "parent" ? (
              <select
                value={camp.draft_status}
                onChange={async e => {
                  const updated = await api.camps.enrich(recordId, { draft_status: e.target.value });
                  setCamp(updated);
                }}
                className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full border-0 cursor-pointer"
              >
                <option value="candidate">candidate</option>
                <option value="draft">draft</option>
                <option value="published">published</option>
                <option value="archived">archived</option>
              </select>
            ) : (
              <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">
                {camp.draft_status}
              </span>
            )
          )}
          {camp.is_excluded && (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full">
              Hidden: not a camp
            </span>
          )}
        </div>
      </div>

      {/* ChatGPT Research Clipboard */}
      {(user?.role === "parent" || user?.role === "child") && (
        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold text-purple-900">🤖 ChatGPT Research</h2>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleCopyPrompt}
                className="bg-purple-600 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-purple-700"
                title="Fills in missing structured fields: ages, grades, pricing, contact info, duration"
              >
                {copied ? "✅ Copied!" : "📋 Copy Metadata Prompt"}
              </button>
              <button
                onClick={handleCopyDeepPrompt}
                className="bg-fuchsia-600 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-fuchsia-700"
                title="Asks ChatGPT for a detailed description, selectivity, curriculum, reputation, and what participants experience"
              >
                {copiedDeep ? "✅ Copied!" : "🔍 Copy Deep Research Prompt"}
              </button>
              <button
                onClick={() => setShowPaste(!showPaste)}
                className="bg-indigo-600 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
              >
                📥 Paste Results
              </button>
            </div>
          </div>
          <div className="text-sm text-purple-800 space-y-1">
            <p><strong>Metadata prompt</strong> — fills in ages, grades, pricing, contact info, and confirms overnight/active status.</p>
            <p><strong>Deep research prompt</strong> — asks ChatGPT to write a detailed description: curriculum, selectivity, application tips, and what participants experience.</p>
            <p>Both return JSON you can paste below.</p>
          </div>

          {/* Prompt preview */}
          {showClipboard && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-purple-800">{clipboardLabel}</span>
                <button
                  onClick={() => setShowClipboard(false)}
                  className="text-xs text-purple-500 hover:text-purple-700 px-2"
                >
                  ✕ Close
                </button>
              </div>
              <pre className="bg-white border border-purple-100 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap text-sm text-gray-700 max-h-64 overflow-y-auto">
                {clipboardText}
              </pre>
            </div>
          )}

          {/* Paste section */}
          {showPaste && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-indigo-800">Paste ChatGPT&apos;s JSON response:</span>
                <button
                  onClick={() => { setShowPaste(false); setImportResult(""); }}
                  className="text-xs text-indigo-500 hover:text-indigo-700 px-2"
                >
                  ✕ Close
                </button>
              </div>
              <textarea
                value={pasteText}
                onChange={e => setPasteText(e.target.value)}
                rows={12}
                placeholder={'{\n  "ages_min": 10,\n  "ages_max": 17,\n  "pricing_min": 1500,\n  ...\n}'}
                className="w-full border border-indigo-200 rounded-lg px-3 py-2 text-sm font-mono bg-white text-gray-900 mb-3"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={handleImportEnrichment}
                  disabled={!pasteText.trim()}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  Apply Enrichment
                </button>
                {importResult && (
                  <span className={`text-sm ${importResult.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>
                    {importResult}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
        <h2 className="text-lg font-bold text-blue-900">✏️ Add Or Correct Info</h2>
        <p className="text-sm text-blue-800 mt-2">
          Use a contribution draft to add evidence, fix missing details, or suggest a correction for this camp.
          Contributions are reviewed before they become part of the published research.
        </p>
        {authLoading ? (
          <p className="text-sm text-blue-700 mt-4">Checking your sign-in status…</p>
        ) : user ? (
          <div className="flex flex-wrap gap-3 mt-4">
            <Link
              href={contributionHref}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700"
            >
              Add Info Through a Mission
            </Link>
            <Link
              href="/contributions"
              className="bg-white text-blue-700 px-4 py-2 rounded-lg font-medium border border-blue-200 hover:bg-blue-100"
            >
              Open Contributions
            </Link>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3 mt-4">
            <Link
              href="/login"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700"
            >
              Sign In To Add Info
            </Link>
            <Link
              href="/register"
              className="bg-white text-blue-700 px-4 py-2 rounded-lg font-medium border border-blue-200 hover:bg-blue-100"
            >
              Create Contributor Account
            </Link>
          </div>
        )}
      </div>

      {(user?.role === "parent" || user?.role === "child") && (
        <div className={`rounded-2xl border p-6 ${camp.is_excluded ? "border-red-200 bg-red-50" : "border-orange-200 bg-orange-50"}`}>
          <h2 className={`text-lg font-bold ${camp.is_excluded ? "text-red-900" : "text-orange-900"}`}>
            {camp.is_excluded ? "🚫 Hidden From Public Catalog" : (user?.role === "parent" ? "🧹 Candidate Triage" : "🚩 Flag This Record")}
          </h2>
          {camp.is_excluded ? (
            <>
              <p className="mt-2 text-sm text-red-800">
                This record is currently hidden as a non-camp or out-of-scope result.
              </p>
              {(camp.exclusion_reason || camp.exclusion_notes) && (
                <div className="mt-3 rounded-xl bg-white/70 p-4 text-sm text-red-900">
                  {camp.exclusion_reason && (
                    <p>
                      <span className="font-medium">Reason:</span> {formatModerationReason(camp.exclusion_reason)}
                    </p>
                  )}
                  {camp.exclusion_notes && (
                    <p className="mt-1 whitespace-pre-wrap">{camp.exclusion_notes}</p>
                  )}
                </div>
              )}
              {user?.role === "parent" && (
                <button
                  onClick={() => handleModeration(false)}
                  disabled={moderating}
                  className="mt-4 rounded-lg bg-white px-4 py-2 font-medium text-red-700 border border-red-200 hover:bg-red-100 disabled:opacity-50"
                >
                  {moderating ? "Restoring…" : "Restore To Catalog"}
                </button>
              )}
            </>
          ) : user?.role === "parent" ? (
            <>
              <p className="mt-2 text-sm text-orange-800">
                If this is clearly junk, unrelated, or not an overnight/residential youth program, hide it from the public catalog here.
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-orange-900 mb-1">Reason</label>
                  <select
                    value={moderationReason}
                    onChange={e => setModerationReason(e.target.value)}
                    className="w-full rounded-lg border border-orange-200 bg-white px-3 py-2 text-sm"
                  >
                    <option value="not_a_camp">Not a camp</option>
                    <option value="not_overnight">Not overnight / not residential</option>
                    <option value="duplicate_or_wrong_venue">Duplicate or wrong venue</option>
                    <option value="inactive_or_out_of_scope">Inactive or out of scope</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="md:col-span-1">
                  <label className="block text-sm font-medium text-orange-900 mb-1">Notes</label>
                  <textarea
                    value={moderationNotes}
                    onChange={e => setModerationNotes(e.target.value)}
                    rows={3}
                    placeholder="Why this obviously should not stay in the public catalog…"
                    className="w-full rounded-lg border border-orange-200 bg-white px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <button
                onClick={() => handleModeration(true)}
                disabled={moderating}
                className="mt-4 rounded-lg bg-orange-600 px-4 py-2 font-medium text-white hover:bg-orange-700 disabled:opacity-50"
              >
                {moderating ? "Hiding…" : "Mark Not A Camp"}
              </button>
            </>
          ) : (
            <>
              <p className="mt-2 text-sm text-orange-800">
                Something seem off? Flag this record and it will be hidden from the catalog.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  onClick={() => { setModerationReason("not_a_camp"); handleModeration(true); }}
                  disabled={moderating}
                  className="rounded-lg bg-orange-600 px-4 py-2 font-medium text-white hover:bg-orange-700 disabled:opacity-50 text-sm"
                >
                  {moderating ? "Flagging…" : "🚫 Not a Camp"}
                </button>
                <button
                  onClick={() => { setModerationReason("duplicate_or_wrong_venue"); handleModeration(true); }}
                  disabled={moderating}
                  className="rounded-lg bg-orange-500 px-4 py-2 font-medium text-white hover:bg-orange-600 disabled:opacity-50 text-sm"
                >
                  {moderating ? "Flagging…" : "🔗 Duplicate / Wrong Venue"}
                </button>
              </div>
            </>
          )}
          {actionError && <p className="mt-3 text-sm text-red-700">{actionError}</p>}
        </div>
      )}

      {/* Key Details */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">📋 Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          {camp.operator_name && (
            <Detail label="Operator" value={camp.operator_name} />
          )}
          {camp.venue_name && (
            <Detail label="Venue" value={camp.venue_name} />
          )}
          {(camp.ages_min || camp.ages_max) && (
            <Detail label="Ages" value={`${camp.ages_min ?? "?"} – ${camp.ages_max ?? "?"}`} />
          )}
          {(camp.grades_min || camp.grades_max) && (
            <Detail label="Grades" value={`${camp.grades_min ?? "?"} – ${camp.grades_max ?? "?"}`} />
          )}
          {(camp.duration_min_days || camp.duration_max_days) && (
            <Detail label="Duration" value={`${camp.duration_min_days ?? "?"} – ${camp.duration_max_days ?? "?"} days`} />
          )}
          {(camp.pricing_min != null || camp.pricing_max != null) && (
            <Detail
              label="Pricing"
              value={`${camp.pricing_currency || "USD"} $${camp.pricing_min ?? "?"}–$${camp.pricing_max ?? "?"}`}
            />
          )}
          {camp.boarding_included !== null && (
            <Detail label="Boarding Included" value={camp.boarding_included ? "Yes" : "No"} />
          )}
          {camp.website_url && (
            <div>
              <span className="font-medium text-gray-700">Website: </span>
              <a
                href={camp.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline break-all"
              >
                {camp.website_url}
              </a>
            </div>
          )}
          {camp.contact_email && (
            <Detail label="Email" value={camp.contact_email} />
          )}
          {camp.contact_phone && (
            <Detail label="Phone" value={camp.contact_phone} />
          )}
          {camp.last_verified && (
            <Detail label="Last Verified" value={camp.last_verified} />
          )}
        </div>
      </div>

      {/* Program Types */}
      {(families.length > 0 || types.length > 0) && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-3">🎯 Program Types</h2>
          <div className="flex flex-wrap gap-2">
            {families.map(f => (
              <span key={f} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm">
                {formatProgramFamily(f)}
              </span>
            ))}
            {types.map(t => (
              <span key={t} className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm italic">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Plans this camp is on */}
      {user && campPlans.length > 0 && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-3">📋 On Your Plans</h2>
          <ul className="space-y-2">
            {campPlans.map(p => (
              <li key={p.shortlist_item_id} className="flex items-center justify-between">
                <Link
                  href={`/plans/${p.plan_id}`}
                  className="text-blue-600 hover:underline font-medium"
                >
                  {p.plan_title} ({p.plan_year})
                </Link>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full capitalize">
                  {p.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Description / Full Dossier */}
      {camp.description_md && (
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-3">📝 Full Dossier</h2>
          <div className="prose prose-sm max-w-none text-gray-700">
            <ReactMarkdown>{camp.description_md}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="font-medium text-gray-700">{label}: </span>
      <span className="text-gray-600">{value}</span>
    </div>
  );
}

function formatModerationReason(reason: string): string {
  return reason.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}
