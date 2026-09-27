import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Submission } from "../api/client";
import { maxBridge } from "../max/bridge";

export function Inbox() {
  const [items, setItems] = useState<Submission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const user = maxBridge.getUser();
    const teacherId = user ? String(user.id) : "teacher-stub";

    api
      .listSubmissions(teacherId, "checked")
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ padding: 16 }}>Загрузка…</p>;
  if (error) return <p style={{ padding: 16, color: "crimson" }}>{error}</p>;

  return (
    <div style={{ padding: 16 }}>
      <h1 style={{ fontSize: 20 }}>Готовы к проверке</h1>
      {items.length === 0 && <p>Нет работ, ожидающих подтверждения.</p>}
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((s) => (
          <li
            key={s.id}
            style={{
              background: "#fff",
              padding: 12,
              marginBottom: 8,
              borderRadius: 12,
              boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            }}
          >
            <Link to={`/review/${s.id}`}>
              Работа {s.id.slice(0, 8)} · ученик {s.student_id.slice(0, 8)}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
