import { describe, expect, it } from "vitest";

import {
  accountManagerArtifactToCards,
  buildCommercialReviewSlice,
  mergeWarningLists,
  scanTextForReviewWarnings,
  splitMarkdownSections,
  stripMarkdownFences
} from "./reviewDisplayUtils";

describe("scanTextForReviewWarnings", () => {
  it("detects common placeholders", () => {
    const w = scanTextForReviewWarnings("Hello [Customer Name] from [MSP Name]");
    expect(w.length).toBeGreaterThan(0);
    expect(w.some((x) => x.toLowerCase().includes("placeholder"))).toBe(true);
  });

  it("detects fenced markdown", () => {
    const w = scanTextForReviewWarnings("Intro\n```markdown\n# x\n```");
    expect(w.some((x) => x.includes("Fenced"))).toBe(true);
  });
});

describe("stripMarkdownFences", () => {
  it("removes fences", () => {
    expect(stripMarkdownFences("A\n```\ncode\n```\nB")).toBe("A\n\nB");
  });
});

describe("splitMarkdownSections", () => {
  it("splits numbered sections", () => {
    const s = splitMarkdownSections("1. Opener\nHi there.\n\n2. Close\nThanks.");
    expect(s.length).toBeGreaterThanOrEqual(2);
    expect(s[0].title.toLowerCase()).toContain("opener");
  });
});

describe("accountManagerArtifactToCards", () => {
  it("parses markdown text into cards", () => {
    const { cards, placeholderWarnings } = accountManagerArtifactToCards({
    id: "1",
    tenant_id: "t",
    customer_id: "c",
    artifact_type: "account_manager_notes",
    status: "succeeded",
    full_output_json: null,
    full_output_text: "1. Opener\nSay hello.\n\n2. Close\nWrap up.",
    short_context_json: null,
    output_warnings: null,
    created_at: null,
    updated_at: null
  });
    expect(cards.length).toBeGreaterThanOrEqual(2);
    expect(placeholderWarnings).toBeDefined();
  });
});

describe("buildCommercialReviewSlice", () => {
  it("returns honest empty when no rows", () => {
    const d = {
      id: "c",
      name: "Co",
      status: "active",
      owner_name: null,
      latest_scores: null,
      open_tickets_count: 0,
      open_opportunities_count: 0,
      open_quotes_count: 0,
      recommendation_summary: [],
      recent_actions: [],
      contacts: [],
      recommendations: [],
      opportunities: [],
      quotes: []
    };
    const s = buildCommercialReviewSlice(d);
    expect(s.hasCommercialRows).toBe(false);
    expect(s.emptyNote).toBeTruthy();
  });

  it("classifies open and lost", () => {
    const d = {
      id: "c",
      name: "Co",
      status: "active",
      owner_name: null,
      latest_scores: null,
      open_tickets_count: 0,
      open_opportunities_count: 1,
      open_quotes_count: 0,
      recommendation_summary: [],
      recent_actions: [],
      contacts: [],
      recommendations: [],
      opportunities: [
        {
          id: "o1",
          customer_id: "c",
          customer_name: "Co",
          title: "Upsell",
          status: "open",
          value_cents: 10000,
          revisit_reason: "Stalled",
          suggested_next_action: "Book QBR",
          created_at: null
        }
      ],
      quotes: [{ id: "q1", customer_id: "c", customer_name: "Co", title: "Q", status: "lost", value_cents: null, revisit_reason: null, suggested_next_action: "", created_at: null }]
    };
    const s = buildCommercialReviewSlice(d);
    expect(s.openOpportunities.length).toBe(1);
    expect(s.stalledOpportunities.length).toBeGreaterThanOrEqual(1);
    expect(s.lostQuotes.length).toBe(1);
  });
});

describe("mergeWarningLists", () => {
  it("dedupes", () => {
    expect(mergeWarningLists(["a", "b"], ["a"])).toEqual(["a", "b"]);
  });
});
