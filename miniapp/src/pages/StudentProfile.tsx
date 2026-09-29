import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  api,
  type Student,
  type StudentProfile as Profile,
} from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { Loader } from "../components/Loader";

const TREND: Record<
  Profile["trend"],
  { icon: string; label: string; color: string; bg: string }
> = {
  improving: { icon: "↗", label: "растёт", color: "#065f46", bg: "#d1fae5" },
  stable: { icon: "→", label: "стабильно", color: "#1e40af", bg: "#dbeafe" },
  regressing: { icon: "↘", label: "падает", color: "#991b1b", bg: "#fee2e2" },
};

function errorRateColor(rate: number): string {
  if (rate >= 0.6) return "#ef4444";
  if (rate >= 0.3) return "#eab308";
  return "#10b981";
}

export function StudentProfile() {
  const { studentId = "" } = useParams();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [student, setStudent] = useState<Student | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([
      api.getStudentProfile(studentId),
      api.listStudents(),
    ]).then(([p, s]) => {
      if (p.status === "fulfilled") setProfile(p.value);
      else setError(String(p.reason));
      if (s.status === "fulfilled") {
        setStudent(s.value.find((x) => x.id === studentId) ?? null);
      }
    });
  }, [studentId]);

  if (error) return <p className="page" style={{ color: "crimson" }}>{error}</p>;
  if (!profile) return <Loader text="Загрузка профиля…" />;

  const trend = TREND[profile.trend];
  const scorePct = Math.round(profile.avg_score * 100);

  return (
    <div className="page">
      {student && (
        <div style={{ marginBottom: 12 }}>
          <h1 style={{ margin: 0 }}>{student.display_name}</h1>
          <div className="muted-text" style={{ marginTop: 4 }}>
            {student.class_id} · {student.grade} класс
          </div>
        </div>
      )}

      <div className="card">
        <div className="row spread" style={{ marginBottom: 12 }}>
          <div>
            <div className="label">Средний балл</div>
            <b style={{ fontSize: 28, color: errorRateColor(1 - profile.avg_score) }}>
              {profile.avg_score.toFixed(2)}
            </b>
            <span className="muted-text" style={{ marginLeft: 6, fontSize: 13 }}>
              / 1.00
            </span>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="label">Проверено работ</div>
            <b style={{ fontSize: 28 }}>{profile.submissions_count}</b>
          </div>
        </div>

        <div
          style={{
            height: 8,
            background: "#f1f5f9",
            borderRadius: 999,
            overflow: "hidden",
            marginBottom: 12,
          }}
        >
          <div
            style={{
              width: `${scorePct}%`,
              height: "100%",
              background: errorRateColor(1 - profile.avg_score),
              transition: "width 0.3s",
            }}
          />
        </div>

        <span
          className="badge"
          style={{
            background: trend.bg,
            color: trend.color,
            fontSize: 13,
            padding: "4px 10px",
          }}
        >
          {trend.icon} {trend.label}
        </span>
      </div>

      <h2>Слабые темы</h2>
      {profile.weak_topics.length === 0 ? (
        <EmptyState title="Пока не выявлено" hint="Слабых тем нет или мало данных." />
      ) : (
        profile.weak_topics.map((t) => {
          const pct = Math.round(t.error_rate * 100);
          const color = errorRateColor(t.error_rate);
          return (
            <div key={t.topic} className="card">
              <div className="row spread" style={{ marginBottom: 6 }}>
                <b>{t.topic}</b>
                <span style={{ color, fontWeight: 600, fontSize: 13 }}>
                  {pct}% ошибок
                </span>
              </div>
              <div
                style={{
                  height: 6,
                  background: "#f1f5f9",
                  borderRadius: 999,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    background: color,
                  }}
                />
              </div>
            </div>
          );
        })
      )}

      {profile.recurring_mistakes.length > 0 && (
        <>
          <h2>Повторяющиеся ошибки</h2>
          {profile.recurring_mistakes.map((m, i) => (
            <div key={i} className="card">
              <div className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                <span style={{ fontSize: 16, lineHeight: "20px" }}>⚠️</span>
                <span>{m}</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
