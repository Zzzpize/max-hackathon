import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { maxBridge } from "../max/bridge";

const TITLES: [RegExp, string][] = [
  [/^\/$/, "Проверка"],
  [/^\/submit/, "Загрузить фото"],
  [/^\/pick\/work/, "Выбрать работу"],
  [/^\/pick\/student/, "Выбрать ученика"],
  [/^\/works\/new/, "Новая контрольная"],
  [/^\/students\/new/, "Новый ученик"],
  [/^\/review\//, "Проверка работы"],
  [/^\/student\//, "Профиль ученика"],
  [/^\/dashboard\//, "Дашборд класса"],
  [/^\/roadmaps\/new/, "Новый план"],
  [/^\/roadmaps\/[^/]+\/edit/, "Редактировать план"],
  [/^\/roadmaps\/[^/]+$/, "План"],
  [/^\/roadmaps$/, "Планы"],
  [/^\/homework\/new/, "Новая домашка"],
  [/^\/homework\/[^/]+\/edit/, "Редактировать домашку"],
  [/^\/homework\/[^/]+$/, "Домашка"],
  [/^\/homework$/, "Домашки"],
];

function titleFor(pathname: string): string {
  for (const [re, title] of TITLES) if (re.test(pathname)) return title;
  return "Помощник учителя";
}

export function AppBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const isRoot =
    location.pathname === "/" ||
    location.pathname === "/roadmaps" ||
    location.pathname === "/homework";

  useEffect(() => {
    if (isRoot) {
      maxBridge.backButton.hide();
      return;
    }
    maxBridge.backButton.show();
    maxBridge.backButton.onClick(() => navigate(-1));
    return () => maxBridge.backButton.hide();
  }, [isRoot, navigate]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 16px",
        background: "#fff",
        borderBottom: "1px solid rgba(0,0,0,0.05)",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      {!isRoot && (
        <button
          onClick={() => navigate(-1)}
          className="btn subtle"
          style={{ padding: "6px 10px", fontSize: 18 }}
          aria-label="Назад"
        >
          ←
        </button>
      )}
      <div style={{ fontSize: 16, fontWeight: 600 }}>{titleFor(location.pathname)}</div>
    </div>
  );
}
