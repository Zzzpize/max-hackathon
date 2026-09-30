import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Homework } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { Loader } from "../../components/Loader";
import {
  ALL_GRADES,
  subjectLabel,
  SUBJECTS,
} from "../../subjects";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function HomeworkList() {
  const [items, setItems] = useState<Homework[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [subject, setSubject] = useState<string>("");
  const [grade, setGrade] = useState<string>("");
  const [topic, setTopic] = useState<string>("");

  useEffect(() => {
    setItems(null);
    api
      .listHomework({
        subject: subject || undefined,
        grade: grade ? Number(grade) : undefined,
        topic: topic || undefined,
      })
      .then(setItems)
      .catch((e) => {
        setError(String(e));
        setItems([]);
      });
  }, [subject, grade, topic]);

  const showFilters = useMemo(
    () => Boolean(items && items.length > 0) || Boolean(subject || grade || topic),
    [items, subject, grade, topic]
  );

  return (
    <div className="page">
      <h1>Домашние задания</h1>
      <p className="muted-text" style={{ marginTop: -4 }}>
        Сгенерируй набор задач по теме и распечатай — с ответами или без.
      </p>

      <Link
        to="/homework/new"
        className="btn primary wide"
        style={{ display: "block", textAlign: "center", margin: "12px 0" }}
      >
        + Новое задание
      </Link>

      {showFilters && (
        <div className="card">
          <div className="row" style={{ gap: 8 }}>
            <select
              className="input"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="">Все предметы</option>
              {SUBJECTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
            <select
              className="input"
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="">Все классы</option>
              {ALL_GRADES.map((g) => (
                <option key={g} value={g}>
                  {g} класс
                </option>
              ))}
            </select>
          </div>
          <div style={{ height: 8 }} />
          <input
            className="input"
            placeholder="Поиск по теме"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>
      )}

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {items === null ? (
        <Loader text="Загружаю…" />
      ) : items.length === 0 ? (
        <EmptyState
          title="Пусто"
          hint={
            subject || grade || topic
              ? "По фильтрам ничего не нашлось."
              : "Первое задание — по кнопке выше."
          }
        />
      ) : (
        items.map((h) => (
          <Link
            key={h.id}
            to={`/homework/${h.id}`}
            className="card"
            style={{ display: "block" }}
          >
            <div className="row spread">
              <b>{h.title}</b>
              <span className="muted-text">{formatDate(h.created_at)}</span>
            </div>
            <div className="muted-text" style={{ marginTop: 4 }}>
              {subjectLabel(h.subject)} · {h.grade} класс · {h.tasks.length} зад. · {h.topic}
            </div>
          </Link>
        ))
      )}
    </div>
  );
}
