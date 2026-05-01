import type { CustomerDetailResponse, CustomerReviewArtifactOut, OpportunityRow, QuoteRow } from "../api/types";

const PLACEHOLDER_SNIPPETS = [
  "[customer name]",
  "[your name]",
  "[msp name]",
  "<customer>",
  "<msp>",
  "[company name]",
  "[date]"
];

const FENCE_RE = /```[\s\S]*?```/g;

/** Visible scan for bracket placeholders, angle placeholders, and fenced markdown. */
export function scanTextForReviewWarnings(text: string | null | undefined): string[] {
  if (!text || !text.trim()) return [];
  const lower = text.toLowerCase();
  const out: string[] = [];
  for (const p of PLACEHOLDER_SNIPPETS) {
    if (lower.includes(p)) out.push(`Unresolved placeholder pattern: ${p}`);
  }
  if (/\[[^\]]{2,80}\]/.test(text)) {
    const bracket = text.match(/\[[^\]]{2,80}\]/g);
    const suspicious = (bracket ?? []).filter((b) => /name|customer|msp|company|tenant/i.test(b));
    for (const b of suspicious.slice(0, 4)) {
      if (!out.some((w) => w.includes(b))) out.push(`Bracket token may be a placeholder: ${b}`);
    }
  }
  if (FENCE_RE.test(text)) {
    FENCE_RE.lastIndex = 0;
    out.push("Fenced code block detected — not suitable as final customer copy.");
  }
  const leakSnippets = [
    "this is a json",
    "here is the json",
    "here is json",
    "output is json",
    "raw payload",
    "```json",
    "```markdown",
    "canonical row",
    "source_entity",
    "prompt variables",
    "{{customer",
    "{{ msp"
  ];
  for (const s of leakSnippets) {
    if (lower.includes(s)) {
      out.push(`Draft may include implementation wording (${s}) — clean before customer-facing use.`);
    }
  }
  return out;
}

export function stripMarkdownFences(text: string): string {
  return text.replace(FENCE_RE, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

export type MarkdownSection = { title: string; body: string };

/** Split markdown-ish AM output into titled sections (headings, numbered sections, or bold-only lines). */
export function splitMarkdownSections(raw: string): MarkdownSection[] {
  const text = stripMarkdownFences(raw).trim();
  if (!text) return [];
  const lines = text.split(/\n/);
  const sections: MarkdownSection[] = [];
  let title = "Notes";
  const buf: string[] = [];
  const flush = () => {
    const body = buf.join("\n").trim();
    buf.length = 0;
    if (body || title !== "Notes") sections.push({ title, body: body || "—" });
  };
  for (const line of lines) {
    const h1 = line.match(/^#{1,3}\s+(.+)$/);
    const h2 = line.match(/^\d+\.\s*(.+)$/);
    const h3 = line.match(/^\*\*(.+?)\*\*\s*:?\s*$/);
    if (h1 || h2 || h3) {
      flush();
      title = (h1?.[1] ?? h2?.[1] ?? h3?.[1] ?? line).trim();
    } else {
      buf.push(line);
    }
  }
  flush();
  return sections.length ? sections : [{ title: "Notes", body: text }];
}

export type AmDisplayCard = { id: string; title: string; bullets: string[]; body: string };

function linesToBullets(body: string): string[] {
  const out: string[] = [];
  for (const line of body.split(/\n/)) {
    const m = line.match(/^\s*[-*]\s+(.+)$/);
    if (m) out.push(m[1].trim());
    else if (line.trim() && !line.trim().startsWith("#")) {
      const t = line.trim();
      if (t.length < 240) out.push(t);
    }
  }
  return out.length ? out.slice(0, 12) : body ? [body.replace(/\s+/g, " ").trim().slice(0, 400)] : [];
}

function slugId(title: string, i: number): string {
  const s = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${s || "section"}-${i}`;
}

/** Turn persisted AM notes / call script into meeting-pack cards (JSON-aware, then markdown). */
export function accountManagerArtifactToCards(artifact: CustomerReviewArtifactOut | null): {
  cards: AmDisplayCard[];
  placeholderWarnings: string[];
} {
  if (!artifact) return { cards: [], placeholderWarnings: [] };
  const json = artifact.full_output_json;
  const text = artifact.full_output_text ?? "";
  const combined = [
    text,
    json && typeof json === "object" ? JSON.stringify(json) : ""
  ].join("\n");
  let placeholderWarnings = [...scanTextForReviewWarnings(combined)];
  if (artifact.output_warnings?.length) {
    placeholderWarnings = [...new Set([...placeholderWarnings, ...artifact.output_warnings])];
  }

  if (json && typeof json === "object" && !Array.isArray(json)) {
    const o = json as Record<string, unknown>;
    const cardDefs: { key: string; title: string }[] = [
      { key: "opener", title: "Opener" },
      { key: "opening_lines", title: "Opening lines" },
      { key: "opening", title: "Opening" },
      { key: "value_recap", title: "Value recap" },
      { key: "issues_and_opportunities", title: "Issues & opportunities" },
      { key: "talking_points", title: "Talking points" },
      { key: "questions_to_ask", title: "Questions to ask" },
      { key: "proposed_next_step", title: "Proposed next step" },
      { key: "close", title: "Close" },
      { key: "confidence_notes", title: "Confidence & data notes" },
      { key: "data_gaps", title: "Data gaps" }
    ];
    const cards: AmDisplayCard[] = [];
    let i = 0;
    for (const { key, title } of cardDefs) {
      const v = o[key];
      if (v == null) continue;
      if (typeof v === "string" && v.trim()) {
        cards.push({ id: slugId(title, i++), title, bullets: linesToBullets(v), body: v.trim() });
      } else if (Array.isArray(v) && v.every((x) => typeof x === "string")) {
        cards.push({
          id: slugId(title, i++),
          title,
          bullets: (v as string[]).map((x) => x.trim()).filter(Boolean).slice(0, 12),
          body: (v as string[]).join("\n")
        });
      }
    }
    if (!cards.length && typeof json === "object" && !Array.isArray(json)) {
      const o = json as Record<string, unknown>;
      const skip = new Set(["short_context", "shortContext", "copy_notes", "confidence_notes"]);
      let j = 0;
      for (const [k, v] of Object.entries(o)) {
        if (skip.has(k)) continue;
        const title = k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        if (typeof v === "string" && v.trim()) {
          cards.push({ id: slugId(k, j++), title, bullets: linesToBullets(v), body: v.trim() });
        } else if (Array.isArray(v) && v.every((x) => typeof x === "string")) {
          const arr = v as string[];
          cards.push({
            id: slugId(k, j++),
            title,
            bullets: arr.map((x) => x.trim()).filter(Boolean).slice(0, 12),
            body: arr.join("\n")
          });
        }
      }
    }
    if (cards.length) return { cards, placeholderWarnings };
  }

  const source = text.trim() || (json ? JSON.stringify(json, null, 2) : "");
  const sections = splitMarkdownSections(source);
  const cards: AmDisplayCard[] = sections.map((sec, i) => ({
    id: slugId(sec.title, i),
    title: sec.title,
    bullets: linesToBullets(sec.body),
    body: sec.body
  }));
  return { cards, placeholderWarnings };
}

export function needsCustomerReviewFromArtifact(artifact: CustomerReviewArtifactOut | null | undefined): boolean {
  const q = artifact?.short_context_json?.quality_flags as Record<string, unknown> | undefined;
  return q?.needs_customer_review === true;
}

export function mergeWarningLists(...lists: (string[] | null | undefined)[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const list of lists) {
    for (const w of list ?? []) {
      if (!w || seen.has(w)) continue;
      seen.add(w);
      out.push(w);
    }
  }
  return out;
}

export function formatValueCents(cents: number | null | undefined, currencyCode = "GBP"): string {
  if (cents == null) return "—";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: currencyCode, maximumFractionDigits: 0 }).format(
      cents / 100
    );
  } catch {
    return (cents / 100).toFixed(0);
  }
}

const TERMINAL_OPP = new Set(["won", "lost", "closed", "cancelled", "abandoned"]);

export type CommercialReviewSlice = {
  openOpportunities: OpportunityRow[];
  stalledOpportunities: OpportunityRow[];
  lostQuotes: QuoteRow[];
  hasCommercialRows: boolean;
  discussionAngle: string | null;
  emptyNote: string | null;
};

export function buildCommercialReviewSlice(detail: CustomerDetailResponse): CommercialReviewSlice {
  const opps = detail.opportunities ?? [];
  const quotes = detail.quotes ?? [];
  const hasCommercialRows = opps.length > 0 || quotes.length > 0;
  if (!hasCommercialRows) {
    return {
      openOpportunities: [],
      stalledOpportunities: [],
      lostQuotes: [],
      hasCommercialRows: false,
      discussionAngle: null,
      emptyNote: "No opportunities or quotes are synced for this account yet — commercial cards stay empty until PSA or CRM data is connected."
    };
  }
  const openOpportunities = opps.filter((o) => !TERMINAL_OPP.has((o.status ?? "").toLowerCase()));
  const stalledOpportunities = openOpportunities.filter(
    (o) =>
      /stall|stalled|stuck|hold|dormant|aging|idle|paused/i.test(o.status ?? "") ||
      !!(o.revisit_reason && o.revisit_reason.trim())
  );
  const lostQuotes = quotes.filter((q) => (q.status ?? "").toLowerCase() === "lost");
  const angleSource = stalledOpportunities[0] ?? openOpportunities[0] ?? null;
  const discussionAngle = angleSource?.suggested_next_action?.trim() || null;
  return {
    openOpportunities: openOpportunities.slice(0, 8),
    stalledOpportunities: stalledOpportunities.slice(0, 8),
    lostQuotes: lostQuotes.slice(0, 8),
    hasCommercialRows: true,
    discussionAngle,
    emptyNote: null
  };
}
