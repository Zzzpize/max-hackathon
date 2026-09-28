import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Student } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { Loader } from "../components/Loader";
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

  if (loading) return <Loader text="Загрузка учеников…" />;

  return (
    <div className="page">
      {students.length === 0 ? (
        <EmptyState
          title="Пока нет ни одного ученика"
          hint="Добавь первого."
          action={
            <Link to="/students/new" className="btn primary">
              Добавить
            </Link>
          }
        />
      ) : (
        Object.entries(grouped).map(([classId, list]) => (
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
        ))
      )}
      {students.length > 0 && (
        <Link to="/students/new" className="btn wide" style={{ marginTop: 12 }}>
          + Новый ученик
        </Link>
      )}
    </div>
  );
}
