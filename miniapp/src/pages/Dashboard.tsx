import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

export function Dashboard() {
  const { classId = "" } = useParams();
  const [data, setData] = useState<unknown>(null);

  useEffect(() => {
    api.getClassDashboard(classId).then(setData).catch(() => setData(null));
  }, [classId]);

  return (
    <div style={{ padding: 16 }}>
      <h1 style={{ fontSize: 20 }}>Дашборд класса {classId}</h1>
      <pre style={{ background: "#fff", padding: 12, borderRadius: 12 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
      {/* TODO(frontend): визуализация слабых тем, ленты активности, экспорт отчёта */}
    </div>
  );
}
