import type { ReactNode } from "react";

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="card muted" style={{ textAlign: "center", padding: 20 }}>
      <div style={{ fontSize: 15, marginBottom: 6 }}>{title}</div>
      {hint && (
        <div className="muted-text" style={{ marginBottom: action ? 12 : 0 }}>
          {hint}
        </div>
      )}
      {action}
    </div>
  );
}
