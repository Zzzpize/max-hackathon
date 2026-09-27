import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type ClassDashboard } from "../api/client";
import { useTeacherId } from "../max/useTeacherId";

export function Dashboard() {
  const { classId = "" } = useParams();
  const teacherId = useTeacherId();
  const [data, setData] = useState<ClassDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getClassDashboard(classId, teacherId)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [classId, teacherId]);

  if (error) return <p style={{ padding: 16, color: "crimson" }}>{error}</p>;
  if (!data) return <p style={{ padding: 16 }}>Загрузка…</p>;

  return (
    <div style={{ padding: 16 }}>
      <h1 style={{ fontSize: 20 }}>Дашборд класса {classId}</h1>
      <pre style={{ background: "#fff", padding: 12, borderRadius: 12 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
