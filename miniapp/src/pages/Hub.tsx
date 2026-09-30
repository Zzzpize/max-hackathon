import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type Student,
  type Submission,
  type TeacherState,
  type WorkTemplate,
} from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { subjectLabel } from "../subjects";

type Group = {
  key: string;
  title: string;
  items: Submission[];
};

function groupByDay(submissions: Submission[]): Group[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  const buckets = new Map<string, { title: string; items: Submission[]; order: number }>();
  for (const s of submissions) {
    const d = new Date(s.created_at);
    const dayStart = new Date(d);
    dayStart.setHours(0, 0, 0, 0);

    let key: string;
    let title: string;
    let order: number;
    if (dayStart.getTime() === today.getTime()) {
      key = "today";
      title = "Сегодня";
      order = 0;
    } else if (dayStart.getTime() === yesterday.getTime()) {
      key = "yesterday";
      title = "Вчера";
      order = 1;
    } else if (dayStart > weekAgo) {
      key = dayStart.toISOString().slice(0, 10);
      title = dayStart.toLocaleDateString("ru-RU", { weekday: "long", day: "2-digit", month: "long" });
      order = 2;
    } else {
      key = "older";
      title = "Раньше";
      order = 3;
    }
    let bucket = buckets.get(key);
    if (!bucket) {
      bucket = { title, items: [], order };
      buckets.set(key, bucket);
    }
    bucket.items.push(s);
  }

  return [...buckets.entries()]
    .sort((a, b) => a[1].order - b[1].order || (a[0] < b[0] ? 1 : -1))
    .map(([key, b]) => ({ key, title: b.title, items: b.items }));
}

function statusBadge(status: Submission["status"]) {
  if (status === "pending") return { text: "проверяется…", bg: "#fef3c7", color: "#92400e" };
  if (status === "confirmed") return { text: "подтверждена", bg: "#d1fae5", color: "#065f46" };
  return { text: "на проверку", bg: "#dbeafe", color: "#1e40af" };
}

export function Hub() {
  const [state, setState] = useState<TeacherState | null>(null);
  const [works, setWorks] = useState<WorkTemplate[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [inbox, setInbox] = useState<Submission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    Promise.allSettled([
      api.getState(),
      api.listWorks(),
      api.listStudents(),
      api.listSubmissions(),
    ]).then(([s, w, st, sub]) => {
      if (s.status === "fulfilled") setState(s.value);
      if (w.status === "fulfilled") setWorks(w.value);
      if (st.status === "fulfilled") setStudents(st.value);
      if (sub.status === "fulfilled") setInbox(sub.value);
      const errs = [s, w, st, sub].filter((x) => x.status === "rejected");
      if (errs.length === 4) setError("Не удалось загрузить данные с сервера");
    });
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  }, []);

  const currentWork = works.find((w) => w.id === state?.current_work_id);
  const readyForSubmit = Boolean(currentWork);

  const worksById = useMemo(() => {
    const m = new Map<string, WorkTemplate>();
    for (const w of works) m.set(w.id, w);
    return m;
  }, [works]);

  const studentsById = useMemo(() => {
    const m = new Map<string, Student>();
    for (const s of students) m.set(s.id, s);
    return m;
  }, [students]);

  const groups = useMemo(() => groupByDay(inbox), [inbox]);

  const classes = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of students) {
      const key = s.class_id.trim();
      if (!key) continue;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => a[0].localeCompare(b[0], "ru"))
      .map(([classId, count]) => ({ classId, count }));
  }, [students]);

  const removeStudent = async (id: string, name: string) => {
    if (!window.confirm(`Удалить ученика «${name}»? Все его работы будут удалены.`)) return;
    setBusy(id);
    try {
      await api.deleteStudent(id);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const removeWork = async (id: string, title: string) => {
    if (!window.confirm(`Удалить работу «${title}»? Все загруженные проверки будут удалены.`)) return;
    setBusy(id);
    try {
      await api.deleteWork(id);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="page">
      <h1>Проверка контрольных</h1>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>Текущая работа</h2>
      <div className="card">
        <div className="row spread">
          <div>
            <div className="label">Что проверяем</div>
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
        Загрузить фото работ учеников
      </Link>
      <p className="muted-text" style={{ marginTop: 8 }}>
        Учеников можно выбрать сразу нескольких, каждому — до 10 фото.
      </p>

      <h2>Работы учеников <span className="muted-text">· {inbox.length}</span></h2>
      {groups.length === 0 ? (
        <EmptyState title="Пока пусто" hint="Отправь фото — работы появятся здесь." />
      ) : (
        groups.map((group) => (
          <details key={group.key} open style={{ marginBottom: 12 }}>
            <summary
              style={{
                cursor: "pointer",
                padding: "6px 4px",
                fontSize: 13,
                color: "#4b5563",
                fontWeight: 600,
                textTransform: "capitalize",
              }}
            >
              {group.title} · {group.items.length}
            </summary>
            <div style={{ marginTop: 6 }}>
              {group.items.map((s) => {
                const student = studentsById.get(s.student_id);
                const work = worksById.get(s.work_id);
                const studentName = student?.display_name ?? `Ученик #${s.student_id.slice(0, 6)}`;
                const workTitle = work?.title ?? `Работа #${s.work_id.slice(0, 6)}`;
                const badge = statusBadge(s.status);
                const pending = s.status === "pending";
                const inner = (
                  <>
                    <div className="row spread" style={{ marginBottom: 4 }}>
                      <b style={{ fontSize: 14 }}>{studentName}</b>
                      <span
                        className="badge"
                        style={{ background: badge.bg, color: badge.color }}
                      >
                        {badge.text}
                      </span>
                    </div>
                    <div className="muted-text" style={{ fontSize: 12 }}>
                      {workTitle}
                    </div>
                  </>
                );
                return pending ? (
                  <div key={s.id} className="card" style={{ opacity: 0.7 }}>
                    {inner}
                  </div>
                ) : (
                  <Link
                    key={s.id}
                    to={`/review/${s.id}`}
                    className="card"
                    style={{ display: "block" }}
                  >
                    {inner}
                  </Link>
                );
              })}
            </div>
          </details>
        ))
      )}

      <h2 style={{ marginTop: 32 }}>Мои работы <span className="muted-text">· {works.length}</span></h2>
      <Link to="/works/new" className="btn primary wide" style={{ display: "block", textAlign: "center", marginBottom: 12 }}>
        + Новая работа
      </Link>
      {works.length === 0 ? (
        <EmptyState title="Пока ни одной работы" hint="Создай первую по кнопке выше." />
      ) : (
        <details open>
          <summary
            style={{
              cursor: "pointer",
              padding: "6px 4px",
              fontSize: 13,
              color: "#4b5563",
              fontWeight: 600,
            }}
          >
            Показать все · {works.length}
          </summary>
          <div style={{ marginTop: 6 }}>
            {works.map((w) => (
              <div key={w.id} className="card">
                <div className="row spread">
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 600, marginBottom: 2 }}>{w.title}</div>
                    <div className="muted-text" style={{ fontSize: 12 }}>
                      {subjectLabel(w.subject)} · {w.grade} кл. · {w.tasks.length} зад.
                    </div>
                  </div>
                  <button
                    className="btn subtle danger"
                    onClick={() => removeWork(w.id, w.title)}
                    disabled={busy === w.id}
                    aria-label="Удалить работу"
                    style={{ padding: "4px 10px", fontSize: 18 }}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      <h2 style={{ marginTop: 32 }}>Мои ученики <span className="muted-text">· {students.length}</span></h2>
      <Link to="/students/new" className="btn primary wide" style={{ display: "block", textAlign: "center", marginBottom: 12 }}>
        + Новый ученик
      </Link>
      {students.length === 0 ? (
        <EmptyState title="Пока ни одного ученика" hint="Добавь по кнопке выше." />
      ) : (
        <details open>
          <summary
            style={{
              cursor: "pointer",
              padding: "6px 4px",
              fontSize: 13,
              color: "#4b5563",
              fontWeight: 600,
            }}
          >
            Показать все · {students.length}
          </summary>
          <div style={{ marginTop: 6 }}>
            {students.map((s) => (
              <div key={s.id} className="card">
                <div className="row spread">
                  <Link
                    to={`/student/${s.id}`}
                    style={{ minWidth: 0, flex: 1, display: "block" }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: 2 }}>{s.display_name}</div>
                    <div className="muted-text" style={{ fontSize: 12 }}>
                      {s.class_id} · {s.grade} кл. · открыть профиль →
                    </div>
                  </Link>
                  <button
                    className="btn subtle danger"
                    onClick={() => removeStudent(s.id, s.display_name)}
                    disabled={busy === s.id}
                    aria-label="Удалить ученика"
                    style={{ padding: "4px 10px", fontSize: 18 }}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {classes.length > 0 && (
        <>
          <h2 style={{ marginTop: 32 }}>Дашборды классов</h2>
          <p className="muted-text" style={{ marginTop: -4, marginBottom: 8 }}>
            Средний балл, слабые темы и ученики которым нужна помощь.
          </p>
          {classes.map((cls) => (
            <Link
              key={cls.classId}
              to={`/dashboard/${encodeURIComponent(cls.classId)}`}
              className="card"
              style={{ display: "block" }}
            >
              <div className="row spread">
                <div>
                  <b>{cls.classId}</b>
                  <div className="muted-text" style={{ fontSize: 12 }}>
                    {cls.count} {cls.count === 1 ? "ученик" : cls.count < 5 ? "ученика" : "учеников"}
                  </div>
                </div>
                <span className="muted-text">→</span>
              </div>
            </Link>
          ))}
        </>
      )}
    </div>
  );
}
