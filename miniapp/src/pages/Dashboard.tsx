import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type ClassDashboard } from "../api/client";
import { Loader } from "../components/Loader";

function ProgressBar({
  value,
  color,
}: {
  value: number;
  color: string;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div
      style={{
        height: 8,
        background: "#f1f5f9",
        borderRadius: 999,
        overflow: "hidden",
        flex: 1,
      }}
    >
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: color,
          transition: "width 0.3s",
        }}
      />
    </div>
  );
}

function errorColor(rate: number): string {
  if (rate >= 0.6) return "#ef4444";
  if (rate >= 0.3) return "#eab308";
  return "#10b981";
}

export function Dashboard() {
  const { classId = "" } = useParams();
  const [data, setData] = useState<ClassDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getClassDashboard(classId)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [classId]);

  if (error) return <p className="page" style={{ color: "crimson" }}>{error}</p>;
  if (!data) return <Loader text="Загрузка дашборда…" />;

  const scorePct = Math.round((data.avg_score / 5) * 100);
  const weakTopics = [...data.weak_topics].sort(
    (a, b) => b.error_rate - a.error_rate
  );

  return (
    <div className="page">
      <h1>Класс {data.class_id}</h1>

      <div className="row" style={{ gap: 8, marginBottom: 12 }}>
        <div className="card" style={{ flex: 1, margin: 0 }}>
          <div className="label">Учеников</div>
          <b style={{ fontSize: 22 }}>{data.students_count}</b>
        </div>
        <div className="card" style={{ flex: 1, margin: 0 }}>
          <div className="label">Средний балл</div>
          <b style={{ fontSize: 22, color: errorColor(1 - data.avg_score / 5) }}>
            {data.avg_score.toFixed(1)}
          </b>
          <div style={{ marginTop: 4 }}>
            <ProgressBar
              value={data.avg_score / 5}
              color={errorColor(1 - data.avg_score / 5)}
            />
          </div>
          <div className="muted-text" style={{ fontSize: 11, marginTop: 4 }}>
            {scorePct}% от максимума
          </div>
        </div>
      </div>

      <h2>Слабые темы</h2>
      {weakTopics.length === 0 && (
        <div className="card muted">
          <span className="muted-text">Пока нет данных.</span>
        </div>
      )}
      {weakTopics.map((t) => {
        const pct = Math.round(t.error_rate * 100);
        return (
          <div key={t.topic} className="card">
            <div className="row spread" style={{ marginBottom: 6 }}>
              <b>{t.topic}</b>
              <span
                className="badge"
                style={{
                  background:
                    t.error_rate >= 0.6
                      ? "#fee2e2"
                      : t.error_rate >= 0.3
                      ? "#fef3c7"
                      : "#d1fae5",
                  color:
                    t.error_rate >= 0.6
                      ? "#991b1b"
                      : t.error_rate >= 0.3
                      ? "#92400e"
                      : "#065f46",
                }}
              >
                {pct}% ошибок
              </span>
            </div>
            <ProgressBar
              value={t.error_rate}
              color={errorColor(t.error_rate)}
            />
          </div>
        );
      })}

      <h2>Нужна помощь</h2>
      {data.students_needing_help.length === 0 && (
        <div className="card muted">
          <span className="muted-text">Все в норме.</span>
        </div>
      )}
      {data.students_needing_help.map((s) => (
        <Link
          key={s.student_id}
          to={`/student/${s.student_id}`}
          className="card"
          style={{ display: "block" }}
        >
          <div className="row spread">
            <b>Ученик #{s.student_id.slice(0, 6)}</b>
            <span className="muted-text">→</span>
          </div>
          <div className="muted-text">{s.reason}</div>
        </Link>
      ))}
    </div>
  );
}
