import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Roadmap } from "../../api/client";
import { Loader } from "../../components/Loader";
import { subjectLabel } from "../../subjects";

export function RoadmapView() {
  const { roadmapId } = useParams<{ roadmapId: string }>();
  const navigate = useNavigate();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!roadmapId) return;
    api
      .getRoadmap(roadmapId)
      .then(setRoadmap)
      .catch((e) => setError(String(e)));
  }, [roadmapId]);

  const remove = async () => {
    if (!roadmapId) return;
    if (!window.confirm("Удалить план? Действие необратимо.")) return;
    try {
      await api.deleteRoadmap(roadmapId);
      navigate("/roadmaps", { replace: true });
    } catch (e) {
      setError(String(e));
    }
  };

  const regenerate = async (index: number) => {
    if (!roadmapId) return;
    const refine = window.prompt("Что именно поправить в этом блоке? (можно пусто)") ?? "";
    setRegenerating(index);
    try {
      const updated = await api.regenerateRoadmapSegment(roadmapId, index, refine);
      setRoadmap(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setRegenerating(null);
    }
  };

  if (!roadmap && !error) return <Loader text="Загружаю план…" />;
  if (error) return <div className="page"><p style={{ color: "crimson" }}>{error}</p></div>;
  if (!roadmap) return null;

  return (
    <div className="page">
      <div className="row spread" style={{ marginBottom: 8 }}>
        <div>
          <h1 style={{ margin: 0 }}>{roadmap.title}</h1>
          <div className="muted-text" style={{ marginTop: 4 }}>
            {subjectLabel(roadmap.subject)} · {roadmap.grade} класс · {roadmap.content.segments.length} блоков
          </div>
        </div>
        <button
          className="btn subtle"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Меню"
          style={{ fontSize: 20 }}
        >
          ⋮
        </button>
      </div>

      {menuOpen && (
        <div className="card">
          <Link
            to={`/roadmaps/${roadmap.id}/edit`}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ✏️ Редактировать
          </Link>
          <a
            href={api.roadmapExportUrl(roadmap.id, "txt")}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ⬇ Скачать TXT
          </a>
          <a
            href={api.roadmapExportUrl(roadmap.id, "pdf")}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ⬇ Скачать PDF
          </a>
          <button className="btn danger wide" onClick={remove}>
            Удалить план
          </button>
        </div>
      )}

      {roadmap.content.segments.map((seg) => (
        <div key={seg.index} className="card">
          <div className="row spread" style={{ marginBottom: 6 }}>
            <b>Недели {seg.weeks} · {seg.hours} ч</b>
            <button
              className="btn subtle"
              onClick={() => regenerate(seg.index)}
              disabled={regenerating !== null}
            >
              {regenerating === seg.index ? "…" : "✏️"}
            </button>
          </div>
          <div style={{ marginBottom: 6 }}>
            <div className="label">Тема</div>
            <div>{seg.topic}</div>
          </div>
          {seg.objectives && (
            <div style={{ marginBottom: 6 }}>
              <div className="label">Цель</div>
              <div>{seg.objectives}</div>
            </div>
          )}
          {seg.materials_hint && (
            <div>
              <div className="label">Материалы</div>
              <div className="muted-text">{seg.materials_hint}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
