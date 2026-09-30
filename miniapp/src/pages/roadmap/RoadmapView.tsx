import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadAuthorized, type Roadmap } from "../../api/client";
import { Loader } from "../../components/Loader";
import { subjectLabel } from "../../subjects";

function sanitizeFilename(name: string): string {
  const cleaned = name.replace(/[\\/:*?"<>|]+/g, "").trim();
  return cleaned || "roadmap";
}

export function RoadmapView() {
  const { roadmapId } = useParams<{ roadmapId: string }>();
  const navigate = useNavigate();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

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
    const refine = window.prompt(
      "Что именно поправить в этом блоке? Опиши, что не так или что хочется."
    );
    if (refine === null) return;
    const trimmed = refine.trim();
    if (!trimmed) {
      setError("Опиши, что поправить — без этого модель не поймёт задачу.");
      return;
    }
    setError(null);
    setRegenerating(index);
    try {
      const updated = await api.regenerateRoadmapSegment(roadmapId, index, trimmed);
      setRoadmap(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setRegenerating(null);
    }
  };

  const download = async (format: "txt" | "pdf") => {
    if (!roadmap) return;
    setBusy(format);
    setError(null);
    try {
      const filename = `${sanitizeFilename(roadmap.title)}.${format}`;
      await downloadAuthorized(`/roadmaps/${roadmap.id}/export?format=${format}`, filename);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const segmentToHomework = (topic: string) => {
    if (!roadmap) return;
    const params = new URLSearchParams({
      subject: roadmap.subject,
      grade: String(roadmap.grade),
      topic,
    });
    navigate(`/homework/new?${params.toString()}`);
  };

  if (!roadmap && !error) return <Loader text="Загружаю план…" />;
  if (error && !roadmap) return <div className="page"><p style={{ color: "crimson" }}>{error}</p></div>;
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

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {menuOpen && (
        <div className="card">
          <Link
            to={`/roadmaps/${roadmap.id}/edit`}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ✏️ Редактировать
          </Link>
          <button
            className="btn wide"
            onClick={() => download("txt")}
            disabled={busy !== null}
            style={{ marginBottom: 6 }}
          >
            {busy === "txt" ? "Скачиваю…" : "⬇ Скачать TXT"}
          </button>
          <button
            className="btn wide"
            onClick={() => download("pdf")}
            disabled={busy !== null}
            style={{ marginBottom: 6 }}
          >
            {busy === "pdf" ? "Скачиваю…" : "⬇ Скачать PDF"}
          </button>
          <button className="btn danger wide" onClick={remove}>
            Удалить план
          </button>
        </div>
      )}

      {roadmap.content.segments.map((seg) => (
        <div key={seg.index} className="card">
          <div className="row spread" style={{ marginBottom: 6 }}>
            <b>Недели {seg.weeks} · {seg.hours} ч</b>
            <div className="row" style={{ gap: 4 }}>
              <button
                className="btn subtle"
                onClick={() => segmentToHomework(seg.topic)}
                aria-label="Создать задание по теме"
                title="Создать домашнее задание по теме"
              >
                📝
              </button>
              <button
                className="btn subtle"
                onClick={() => regenerate(seg.index)}
                disabled={regenerating !== null}
                aria-label="Перегенерировать блок"
              >
                {regenerating === seg.index ? "…" : "✏️"}
              </button>
            </div>
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
