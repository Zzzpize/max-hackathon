import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Roadmap, type RoadmapSegment } from "../../api/client";
import { Loader } from "../../components/Loader";

type EditableSegment = RoadmapSegment;

export function RoadmapEdit() {
  const { roadmapId } = useParams<{ roadmapId: string }>();
  const navigate = useNavigate();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [title, setTitle] = useState("");
  const [segments, setSegments] = useState<EditableSegment[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!roadmapId) return;
    api
      .getRoadmap(roadmapId)
      .then((r) => {
        setRoadmap(r);
        setTitle(r.title);
        setSegments(r.content.segments);
      })
      .catch((e) => setError(String(e)));
  }, [roadmapId]);

  const updateSeg = (index: number, patch: Partial<EditableSegment>) =>
    setSegments((prev) =>
      prev.map((s) => (s.index === index ? { ...s, ...patch } : s))
    );

  const removeSeg = (index: number) =>
    setSegments((prev) =>
      prev
        .filter((s) => s.index !== index)
        .map((s, i) => ({ ...s, index: i + 1 }))
    );

  const addSeg = () =>
    setSegments((prev) => [
      ...prev,
      {
        index: prev.length + 1,
        weeks: "",
        topic: "",
        objectives: "",
        hours: 0,
      },
    ]);

  const save = async () => {
    if (!roadmapId) return;
    setSaving(true);
    setError(null);
    try {
      await api.patchRoadmap(roadmapId, {
        title: title.trim(),
        content: { segments },
      });
      navigate(`/roadmaps/${roadmapId}`, { replace: true });
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  };

  if (!roadmap && !error) return <Loader text="Загружаю…" />;
  if (error && !roadmap)
    return <div className="page"><p style={{ color: "crimson" }}>{error}</p></div>;
  if (!roadmap) return null;

  return (
    <div className="page">
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <label className="label">Название</label>
        <input
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>

      <h2>Блоки</h2>
      {segments.map((s) => (
        <div key={s.index} className="card">
          <div className="row spread" style={{ marginBottom: 6 }}>
            <b>Блок {s.index}</b>
            <button
              className="btn subtle danger"
              onClick={() => removeSeg(s.index)}
            >
              Удалить
            </button>
          </div>
          <label className="label">Недели</label>
          <input
            className="input"
            placeholder="1-2"
            value={s.weeks}
            onChange={(e) => updateSeg(s.index, { weeks: e.target.value })}
          />
          <div style={{ height: 6 }} />
          <label className="label">Часы</label>
          <input
            className="input"
            type="number"
            min={0}
            value={s.hours}
            onChange={(e) =>
              updateSeg(s.index, { hours: Number(e.target.value) || 0 })
            }
          />
          <div style={{ height: 6 }} />
          <label className="label">Тема</label>
          <input
            className="input"
            value={s.topic}
            onChange={(e) => updateSeg(s.index, { topic: e.target.value })}
          />
          <div style={{ height: 6 }} />
          <label className="label">Цель</label>
          <textarea
            className="textarea"
            value={s.objectives}
            onChange={(e) => updateSeg(s.index, { objectives: e.target.value })}
          />
          <div style={{ height: 6 }} />
          <label className="label">Материалы</label>
          <textarea
            className="textarea"
            value={s.materials_hint ?? ""}
            onChange={(e) =>
              updateSeg(s.index, { materials_hint: e.target.value })
            }
          />
        </div>
      ))}

      <button className="btn wide" onClick={addSeg}>
        + Добавить блок
      </button>

      <div style={{ height: 12 }} />
      <button
        className="btn primary wide"
        onClick={save}
        disabled={saving || !title.trim() || segments.length === 0}
      >
        {saving ? "Сохраняю…" : "Сохранить"}
      </button>
    </div>
  );
}
