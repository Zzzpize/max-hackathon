import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Student } from "../api/client";
import { useTeacherId } from "../max/useTeacherId";

export function StudentPicker() {
  const teacherId = useTeacherId();
  const navigate = useNavigate();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState<string | null>(null);

  useEffect(() => {
    api
      .listStudents(teacherId)
      .then(setStudents)
      .catch(() => setStudents([]))
      .finally(() => setLoading(false));
  }, [teacherId]);

  const pick = async (id: string) => {
    setSelecting(id);
    try {
      await api.setState(teacherId, { current_student_id: id });
      navigate("/");
    } finally {
      setSelecting(null);
    }
  };

  const grouped = students.reduce<Record<string, Student[]>>((acc, s) => {
    (acc[s.class_id] ??= []).push(s);
    return acc;
  }, {});

  return (
    <div className="page">
      <h1>Выбрать ученика</h1>
      {loading && <p className="muted-text">Загрузка…</p>}
      {!loading && students.length === 0 && (
        <div className="card muted">
          <p>Пока нет ни одного ученика.</p>
          <Link to="/students/new" className="btn primary">
            Добавить первого
          </Link>
        </div>
      )}
      {Object.entries(grouped).map(([classId, list]) => (
        <div key={classId}>
          <h2>{classId}</h2>
          {list.map((s) => (
            <button
              key={s.id}
              className="card"
              onClick={() => pick(s.id)}
              disabled={selecting !== null}
              style={{ width: "100%", textAlign: "left", border: "none" }}
            >
              {s.display_name}
            </button>
          ))}
        </div>
      ))}
      <Link to="/students/new" className="btn wide" style={{ marginTop: 12 }}>
        + Новый ученик
      </Link>
    </div>
  );
}
