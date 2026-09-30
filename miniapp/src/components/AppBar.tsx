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
  [/^\/homework\/new/, "Новое задание"],
  [/^\/homework\/[^/]+\/edit/, "Редактировать задание"],
  [/^\/homework\/[^/]+$/, "Домашнее задание"],
  [/^\/homework$/, "Домашние задания"],
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
    maxBridge.backButton.setHandler(() => navigate(-1));
    if (isRoot) maxBridge.backButton.hide();
    else maxBridge.backButton.show();
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
