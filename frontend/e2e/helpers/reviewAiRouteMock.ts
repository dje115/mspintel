import type { Page, Route } from "@playwright/test";

type Meta = { tenantId: string; customerId: string };

const rnd = () => crypto.randomUUID();

function isoNow() {
  return new Date().toISOString();
}

/** Minimal ReviewAiGenerationResponse + CustomerReviewArtifactOut fields the UI reads. */
export function installReviewAiMocks(page: Page, meta: Meta) {
  const history: Record<string, unknown>[] = [];
  const latest: Record<string, Record<string, unknown> | null> = {
    review_agenda: null,
    customer_email_draft: null,
    customer_report: null,
    account_manager_notes: null,
    call_script: null
  };

  const pushHistory = (row: Record<string, unknown>) => {
    history.unshift(row);
  };

  const mkArtifact = (
    artifactType: string,
    fullJson: Record<string, unknown> | null,
    title: string
  ): Record<string, unknown> => {
    const id = rnd();
    const row = {
      id,
      tenant_id: meta.tenantId,
      customer_id: meta.customerId,
      artifact_type: artifactType,
      title,
      status: "succeeded",
      full_output_json: fullJson,
      full_output_text: null,
      short_context_json: { summary: `${artifactType} smoke summary`, key_points: [] },
      created_by_user_id: null,
      ai_task_run_id: rnd(),
      prompt_key: `${artifactType}.system`,
      prompt_version_id: rnd(),
      provider_family: "mock",
      deployment_mode: "hosted",
      model_used: "e2e-mock",
      source_data_version: "e2e",
      source_coverage_summary: {},
      output_warnings: [],
      created_at: isoNow(),
      updated_at: isoNow()
    };
    latest[artifactType] = row;
    pushHistory({ ...row });
    return row;
  };

  const genResponse = (
    taskType: string,
    structured: Record<string, unknown> | null,
    artifactType: string
  ) => {
    const art = mkArtifact(artifactType, structured, structured?.meeting_title?.toString() ?? artifactType);
    return {
      run_id: rnd(),
      status: "succeeded",
      task_type: taskType,
      text: null,
      message: null,
      provider_family: "mock",
      deployment_mode: "hosted",
      model_used: "e2e-mock",
      prompt_definition_id: rnd(),
      prompt_version_id: rnd(),
      fallback_used: false,
      duration_ms: 12,
      completed_at: isoNow(),
      artifact_id: art.id,
      structured_output: structured,
      short_context: { summary: "e2e mock" },
      output_warnings: []
    };
  };

  const handler = async (route: Route) => {
    const url = route.request().url();
    const method = route.request().method();
    if (!url.includes(`/api/v1/reviews/${meta.customerId}/`)) {
      await route.continue();
      return;
    }

    const pathname = new URL(url).pathname;
    const isLatest = pathname.endsWith("/ai/artifacts/latest");
    const isList = pathname.endsWith("/ai/artifacts");

    if (method === "GET" && isLatest) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ by_type: latest }) });
      return;
    }
    if (method === "GET" && isList) {
      let rows = history.slice(0, 40);
      const filterType = new URL(url).searchParams.get("artifact_type");
      if (filterType) {
        rows = rows.filter((r) => (r as { artifact_type?: string }).artifact_type === filterType);
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: rows })
      });
      return;
    }

    if (method === "POST" && pathname.endsWith("/ai/agenda")) {
      const structured = {
        meeting_title: "E2E agenda",
        objectives: ["Align priorities"],
        agenda_sections: [{ title: "Intro", duration_minutes: 5, talking_points: ["Welcome"] }],
        suggested_questions: [],
        follow_up_actions: [],
        confidence_notes: []
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(genResponse("customer_review_agenda", structured, "review_agenda"))
      });
      return;
    }
    if (method === "POST" && pathname.includes("/ai/email-draft")) {
      const structured = {
        subject: "Quarterly review — Acme Corp",
        body: "Hello,\n\nWe would like to schedule your service review.\n\nRegards,\nDemo MSP",
        copy_notes: [],
        confidence_notes: []
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(genResponse("customer_review_email_draft", structured, "customer_email_draft"))
      });
      return;
    }
    if (method === "POST" && pathname.endsWith("/ai/customer-report")) {
      const structured = {
        title: "Acme — review brief",
        executive_summary: "Executive summary from e2e mock.",
        highlights: [{ label: "Engagement", detail: "Strong partnership" }],
        service_snapshot: [],
        m365_snapshot: [],
        risks_and_actions: [],
        recommendations: [],
        next_steps: [],
        data_notes: [],
        confidence_notes: []
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(genResponse("customer_review_report", structured, "customer_report"))
      });
      return;
    }

    await route.continue();
  };

  void page.route("**/api/v1/reviews/**", handler);
  return () => {
    void page.unroute("**/api/v1/reviews/**", handler);
  };
}
