/** Compact score bar for customer lists and 360 views. */
export function ScoreMeter({
  value,
  label,
  variant = "default"
}: {
  value: number | null | undefined;
  label: string;
  variant?: "default" | "risk";
}) {
  const n = value == null ? null : Math.min(100, Math.max(0, value));
  const pct = n == null ? 0 : n;
  return (
    <div className="tenant-score-meter">
      <div className="tenant-score-meter-top">
        <span>{label}</span>
        <span>{n ?? "—"}</span>
      </div>
      <div className="tenant-score-meter-track">
        <div
          className={`tenant-score-meter-fill${variant === "risk" ? " tenant-score-meter-fill--risk" : ""}`}
          style={{ width: n == null ? "0%" : `${pct}%` }}
        />
      </div>
    </div>
  );
}
