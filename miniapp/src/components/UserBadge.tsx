import { maxBridge } from "../max/bridge";

export function UserBadge() {
  const user = maxBridge.getUser();
  const platform = maxBridge.getPlatform();
  const startParam = maxBridge.getStartParam();
  const bridgeReady = maxBridge.isAvailable;

  const style: React.CSSProperties = {
    background: bridgeReady ? "#e0f2fe" : "#fee2e2",
    color: bridgeReady ? "#075985" : "#991b1b",
    padding: "6px 12px",
    fontSize: 12,
    fontFamily: "ui-monospace, SFMono-Regular, monospace",
    borderBottom: "1px solid rgba(0,0,0,0.05)",
    display: "flex",
    justifyContent: "space-between",
    gap: 8,
    flexWrap: "wrap",
  };

  if (!bridgeReady) {
    return (
      <div style={style}>
        <span>MAX Bridge не подключён (вне MAX или ошибка загрузки)</span>
        <span>fallback teacher_id = teacher-stub</span>
      </div>
    );
  }

  const name = user
    ? [user.first_name, user.last_name].filter(Boolean).join(" ") ||
      user.username ||
      "(без имени)"
    : "(нет user)";

  return (
    <div style={style}>
      <span>
        {name} · #{user?.id ?? "?"}
      </span>
      <span>
        {platform}
        {startParam ? ` · start=${startParam}` : ""}
      </span>
    </div>
  );
}
