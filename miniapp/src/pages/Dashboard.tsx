import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type ClassDashboard, type Student } from "../api/client";
import { EmptyState } from "../components/EmptyState";
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
  const [students, setStudents] = useState<Student[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([
      api.getClassDashboard(classId),
      api.listStudents(),
    ]).then(([d, s]) => {
      if (d.status === "fulfilled") setData(d.value);
      else setError(String(d.reason));
      if (s.status === "fulfilled") setStudents(s.value);
    });
  }, [classId]);

  if (error) return <p className="page" style={{ color: "crimson" }}>{error}</p>;
  if (!data) return <Loader text="Загрузка дашборда…" />;

  const studentName = (id: string): string =>
    students.find((s) => s.id === id)?.display_name ?? `Ученик #${id.slice(0, 6)}`;

  const weakTopics = [...data.weak_topics].sort(
    (a, b) => b.error_rate - a.error_rate
  );

  const scoreClamped = Math.max(0, Math.min(1, data.avg_score));

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
          <b style={{ fontSize: 22, color: errorColor(1 - scoreClamped) }}>
            {data.avg_score.toFixed(2)}
          </b>
          <div style={{ marginTop: 6 }}>
            <ProgressBar
              value={scoreClamped}
              color={errorColor(1 - scoreClamped)}
            />
          </div>
        </div>
      </div>

      <h2>Слабые темы</h2>
      {weakTopics.length === 0 ? (
        <EmptyState title="Пока нет данных" />
      ) : (
        weakTopics.map((t) => {
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
        })
      )}

      <h2>Нужна помощь</h2>
      {data.students_needing_help.length === 0 ? (
        <EmptyState title="Все в норме" hint="Никто из класса не отстаёт." />
      ) : (
        data.students_needing_help.map((s) => (
          <Link
            key={s.student_id}
            to={`/student/${s.student_id}`}
            className="card"
            style={{ display: "block" }}
          >
            <div className="row spread">
              <b>{studentName(s.student_id)}</b>
              <span className="muted-text">→</span>
            </div>
            <div className="muted-text" style={{ marginTop: 4 }}>
              {s.reason}
            </div>
          </Link>
        ))
      )}
    </div>
  );
}
