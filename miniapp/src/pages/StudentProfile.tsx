import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type StudentProfile as Profile } from "../api/client";
import { Loader } from "../components/Loader";
import { useTeacherId } from "../max/useTeacherId";

export function StudentProfile() {
  const { studentId = "" } = useParams();
  const teacherId = useTeacherId();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getStudentProfile(studentId, teacherId)
      .then(setProfile)
      .catch((e) => setError(String(e)));
  }, [studentId, teacherId]);

  if (error) return <p style={{ padding: 16, color: "crimson" }}>{error}</p>;
  if (!profile) return <Loader text="Загрузка профиля…" />;

  return (
    <div style={{ padding: 16 }}>
      <h1 style={{ fontSize: 20 }}>Профиль ученика</h1>
      <p>Работ проверено: {profile.submissions_count}</p>
      <p>Средний балл: {profile.avg_score.toFixed(2)}</p>
      <p>Тренд: {profile.trend}</p>

      {profile.weak_topics.length > 0 && (
        <>
          <h2 style={{ fontSize: 16, marginTop: 16 }}>Слабые темы</h2>
          <ul>
            {profile.weak_topics.map((t) => (
              <li key={t.topic}>
                {t.topic} - {(t.error_rate * 100).toFixed(0)}% ошибок
              </li>
            ))}
          </ul>
        </>
      )}

      {profile.recurring_mistakes.length > 0 && (
        <>
          <h2 style={{ fontSize: 16, marginTop: 16 }}>Повторяющиеся ошибки</h2>
          <ul>
            {profile.recurring_mistakes.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
