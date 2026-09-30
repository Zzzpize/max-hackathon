import { NavLink, useLocation } from "react-router-dom";

const TABS = [
  { to: "/roadmaps", icon: "📋", label: "Планы" },
  { to: "/homework", icon: "📝", label: "Задания" },
  { to: "/", icon: "✅", label: "Проверка", end: true },
] as const;

const HIDDEN_ON = [/^\/review\//, /^\/submit/];

export function BottomNav() {
  const { pathname } = useLocation();
  if (HIDDEN_ON.some((re) => re.test(pathname))) return null;

  return (
    <nav
      style={{
        position: "fixed",
        left: 0,
        right: 0,
        bottom: 0,
        height: 56,
        background: "#fff",
        borderTop: "1px solid rgba(0,0,0,0.08)",
        display: "flex",
        zIndex: 20,
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={"end" in tab ? tab.end : false}
          style={({ isActive }) => ({
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 2,
            fontSize: 11,
            color: isActive ? "#2563eb" : "#6b7280",
            fontWeight: isActive ? 600 : 400,
            textDecoration: "none",
          })}
        >
          <span style={{ fontSize: 20, lineHeight: 1 }}>{tab.icon}</span>
          <span>{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
