import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type WorkTemplate } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { Loader } from "../components/Loader";
import { useTeacherId } from "../max/useTeacherId";

export function WorkPicker() {
  const teacherId = useTeacherId();
  const navigate = useNavigate();
  const [works, setWorks] = useState<WorkTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState<string | null>(null);

  useEffect(() => {
    api
      .listWorks(teacherId)
      .then(setWorks)
      .catch(() => setWorks([]))
      .finally(() => setLoading(false));
  }, [teacherId]);

  const pick = async (id: string) => {
    setSelecting(id);
    try {
      await api.setState(teacherId, { current_work_id: id });
      navigate("/");
    } finally {
      setSelecting(null);
    }
  };

  if (loading) return <Loader text="Загрузка работ…" />;

  return (
    <div className="page">
      {works.length === 0 ? (
        <EmptyState
          title="Пока нет ни одной работы"
          hint="Создай первую — задания и эталонные ответы."
          action={
            <Link to="/works/new" className="btn primary">
              Создать
            </Link>
          }
        />
      ) : (
        works.map((w) => (
          <button
            key={w.id}
            className="card"
            onClick={() => pick(w.id)}
            disabled={selecting !== null}
            style={{ width: "100%", textAlign: "left", border: "none" }}
          >
            <div className="row spread">
              <b>{w.title}</b>
              <span className="muted-text">{w.tasks.length} зад.</span>
            </div>
            <div className="muted-text">{w.grade} класс</div>
          </button>
        ))
      )}
      {works.length > 0 && (
        <Link to="/works/new" className="btn wide" style={{ marginTop: 12 }}>
          + Новая работа
        </Link>
      )}
    </div>
  );
}
