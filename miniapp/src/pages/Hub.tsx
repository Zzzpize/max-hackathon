import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type Student,
  type Submission,
  type TeacherState,
  type WorkTemplate,
} from "../api/client";
import { EmptyState } from "../components/EmptyState";

export function Hub() {
  const [state, setState] = useState<TeacherState | null>(null);
  const [works, setWorks] = useState<WorkTemplate[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [inbox, setInbox] = useState<Submission[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([
      api.getState(),
      api.listWorks(),
      api.listStudents(),
      api.listSubmissions("checked"),
    ]).then(([s, w, st, sub]) => {
      if (s.status === "fulfilled") setState(s.value);
      if (w.status === "fulfilled") setWorks(w.value);
      if (st.status === "fulfilled") setStudents(st.value);
      if (sub.status === "fulfilled") setInbox(sub.value);
      const errs = [s, w, st, sub].filter((x) => x.status === "rejected");
      if (errs.length === 4) setError("Не удалось загрузить данные с сервера");
    });
  }, []);

  const currentWork = works.find((w) => w.id === state?.current_work_id);
  const currentStudent = students.find(
    (s) => s.id === state?.current_student_id
  );
  const readyForSubmit = currentWork && currentStudent;

  return (
    <div className="page">
      <h1>Проверка контрольных</h1>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>Текущий выбор</h2>
      <div className="card">
        <div className="row spread">
          <div>
            <div className="label">Работа</div>
            <div>
              {currentWork ? (
                <b>{currentWork.title}</b>
              ) : (
                <span className="muted-text">не выбрана</span>
              )}
            </div>
          </div>
          <Link to="/pick/work" className="btn subtle">
            Сменить
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="row spread">
          <div>
            <div className="label">Ученик</div>
            <div>
              {currentStudent ? (
                <b>
                  {currentStudent.display_name} · {currentStudent.class_id}
                </b>
              ) : (
                <span className="muted-text">не выбран</span>
              )}
            </div>
          </div>
          <Link to="/pick/student" className="btn subtle">
            Сменить
          </Link>
        </div>
      </div>

      <Link
        to="/submit"
        className="btn primary wide"
        style={{
          display: "block",
          textAlign: "center",
          marginTop: 12,
          opacity: readyForSubmit ? 1 : 0.5,
          pointerEvents: readyForSubmit ? "auto" : "none",
        }}
      >
        Загрузить фото работы
      </Link>
      <p className="muted-text" style={{ marginTop: 8 }}>
        Или пришли фото в чат боту — он подхватит текущий выбор.
      </p>

      <h2>Готовы к проверке</h2>
      {inbox.length === 0 ? (
        <EmptyState title="Пока пусто" hint="Работы, готовые к проверке, появятся здесь." />
      ) : (
        inbox.map((s) => (
          <Link key={s.id} to={`/review/${s.id}`} className="card" style={{ display: "block" }}>
            <div className="row spread">
              <span>
                Работа #{s.id.slice(0, 6)} · ученик #{s.student_id.slice(0, 6)}
              </span>
              <span className="badge">на проверку</span>
            </div>
          </Link>
        ))
      )}

      <h2>Мои работы <span className="muted-text">· {works.length}</span></h2>
      {works.length === 0 && (
        <EmptyState title="Пока ни одной работы" hint="Создай первую по кнопке ниже." />
      )}
      {works.slice(0, 3).map((w) => (
        <div key={w.id} className="card">
          <div className="row spread">
            <span>{w.title}</span>
            <span className="muted-text">{w.tasks.length} зад.</span>
          </div>
        </div>
      ))}
      <Link to="/works/new" className="btn wide">
        + Новая работа
      </Link>

      <h2>Мои ученики <span className="muted-text">· {students.length}</span></h2>
      {students.length === 0 && (
        <EmptyState title="Пока ни одного ученика" hint="Добавь по кнопке ниже." />
      )}
      {students.slice(0, 3).map((s) => (
        <div key={s.id} className="card">
          <div className="row spread">
            <span>{s.display_name}</span>
            <span className="muted-text">{s.class_id}</span>
          </div>
        </div>
      ))}
      <Link to="/students/new" className="btn wide">
        + Новый ученик
      </Link>
    </div>
  );
}
