import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Roadmap } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { Loader } from "../../components/Loader";
import { subjectLabel } from "../../subjects";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function RoadmapList() {
  const [items, setItems] = useState<Roadmap[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listRoadmaps()
      .then(setItems)
      .catch((e) => {
        setError(String(e));
        setItems([]);
      });
  }, []);

  if (items === null) return <Loader text="Загружаю планы…" />;

  return (
    <div className="page">
      <h1>Планы</h1>
      <p className="muted-text" style={{ marginTop: -4 }}>
        Годовые и квартальные планы — сгенерируй по своему описанию класса.
      </p>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <Link to="/roadmaps/new" className="btn primary wide" style={{ display: "block", textAlign: "center", margin: "12px 0" }}>
        + Новый план
      </Link>

      {items.length === 0 ? (
        <EmptyState
          title="Планов пока нет"
          hint="Опиши класс, программу и цели — AI соберёт помесячный роадмап."
        />
      ) : (
        items.map((r) => (
          <Link
            key={r.id}
            to={`/roadmaps/${r.id}`}
            className="card"
            style={{ display: "block" }}
          >
            <div className="row spread">
              <b>{r.title}</b>
              <span className="muted-text">{formatDate(r.created_at)}</span>
            </div>
            <div className="muted-text" style={{ marginTop: 4 }}>
              {subjectLabel(r.subject)} · {r.grade} класс · {r.content.segments.length} блоков
            </div>
          </Link>
        ))
      )}
    </div>
  );
}
