import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Loader } from "../components/Loader";
import {
  ALL_GRADES,
  gradesForSubject,
  SUBJECTS,
  subjectsForGrade,
  type SubjectId,
} from "../subjects";

type TaskInput = {
  index: number;
  statement: string;
  expected_answer: string;
  ai?: boolean;
  confidence?: number;
};

export function WorkCreate() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState<SubjectId>("math");
  const [grade, setGrade] = useState<number>(3);
  const [tasks, setTasks] = useState<TaskInput[]>([
    { index: 1, statement: "", expected_answer: "" },
  ]);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableGrades = useMemo(() => gradesForSubject(subject), [subject]);
  const availableSubjects = useMemo(() => subjectsForGrade(grade), [grade]);

  const changeSubject = (next: SubjectId) => {
    setSubject(next);
    const grades = gradesForSubject(next);
    if (!grades.includes(grade)) setGrade(grades[0]);
  };

  const changeGrade = (next: number) => {
    setGrade(next);
    const subs = subjectsForGrade(next);
    if (!subs.some((s) => s.id === subject)) setSubject(subs[0].id);
  };

  const addTask = () =>
    setTasks((prev) => [
      ...prev,
      { index: prev.length + 1, statement: "", expected_answer: "" },
    ]);

  const removeTask = (index: number) =>
    setTasks((prev) =>
      prev.filter((t) => t.index !== index).map((t, i) => ({ ...t, index: i + 1 }))
    );

  const updateTask = (index: number, patch: Partial<TaskInput>) =>
    setTasks((prev) => prev.map((t) => (t.index === index ? { ...t, ...patch } : t)));

  const canSubmit =
    title.trim().length > 0 &&
    tasks.length > 0 &&
    tasks.every((t) => t.statement.trim() && t.expected_answer.trim());

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.createWork({
        title: title.trim(),
        subject,
        grade,
        tasks: tasks.map((t) => ({
          index: t.index,
          statement: t.statement.trim(),
          expected_answer: t.expected_answer.trim(),
        })),
      });
      navigate("/");
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const uploadReference = async (file: File) => {
    setExtracting(true);
    setError(null);
    try {
      const extracted = await api.extractReference(file);
      if (extracted.title) setTitle(extracted.title);
      if (extracted.subject && SUBJECTS.some((s) => s.id === extracted.subject)) {
        changeSubject(extracted.subject as SubjectId);
      }
      if (extracted.grade && ALL_GRADES.includes(extracted.grade as never)) {
        changeGrade(extracted.grade);
      }
      if (extracted.tasks.length > 0) {
        setTasks(
          extracted.tasks.map((t, i) => ({
            index: i + 1,
            statement: t.statement,
            expected_answer: t.expected_answer,
            ai: true,
            confidence: t.confidence,
          }))
        );
      } else {
        setError("Не удалось распознать задания в файле. Проверь качество фото или заполни вручную.");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setExtracting(false);
    }
  };

  if (extracting) return <Loader text="Распознаю задания…" />;

  return (
    <div className="page">
      <div className="card" style={{ background: "#eff6ff" }}>
        <div className="label">Быстрое создание</div>
        <b>Загрузи PDF или фото эталона</b>
        <p className="muted-text" style={{ margin: "4px 0 8px" }}>
          Например, фото тетради лучшего ученика или PDF задачника с ответами
          на последней странице. AI извлечёт задания и ответы, ты только проверишь.
        </p>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,image/*"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) uploadReference(f);
          }}
        />
        <button
          className="btn primary wide"
          onClick={() => fileRef.current?.click()}
        >
          🪄 Загрузить PDF или фото
        </button>
      </div>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <label className="label">Название</label>
        <input
          className="input"
          placeholder="Контрольная №3. Умножение"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div style={{ height: 8 }} />
        <label className="label">Предмет</label>
        <select
          className="input"
          value={subject}
          onChange={(e) => changeSubject(e.target.value as SubjectId)}
        >
          {availableSubjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <div style={{ height: 8 }} />
        <label className="label">Класс</label>
        <select
          className="input"
          value={grade}
          onChange={(e) => changeGrade(Number(e.target.value))}
        >
          {availableGrades.map((g) => (
            <option key={g} value={g}>
              {g} класс
            </option>
          ))}
        </select>
      </div>

      <h2>Задания</h2>
      {tasks.map((t) => (
        <div
          key={t.index}
          className="card"
          style={
            t.ai
              ? {
                  border:
                    t.confidence !== undefined && t.confidence < 0.7
                      ? "1px solid #ffb020"
                      : "1px solid #93c5fd",
                }
              : undefined
          }
        >
          <div className="row spread" style={{ marginBottom: 6 }}>
            <div className="row" style={{ gap: 6 }}>
              <b>Задание {t.index}</b>
              {t.ai && (
                <span
                  className="badge"
                  style={
                    t.confidence !== undefined && t.confidence < 0.7
                      ? { background: "#fef3c7", color: "#92400e" }
                      : {}
                  }
                >
                  {t.confidence !== undefined && t.confidence < 0.7
                    ? "AI · проверь"
                    : "AI"}
                </span>
              )}
            </div>
            {tasks.length > 1 && (
              <button
                className="btn subtle danger"
                onClick={() => removeTask(t.index)}
              >
                Удалить
              </button>
            )}
          </div>
          <label className="label">Условие</label>
          <textarea
            className="textarea"
            placeholder="17 × 4 = ?"
            value={t.statement}
            onChange={(e) =>
              updateTask(t.index, { statement: e.target.value, ai: false })
            }
          />
          <div style={{ height: 6 }} />
          <label className="label">Эталонный ответ</label>
          <input
            className="input"
            placeholder="68"
            value={t.expected_answer}
            onChange={(e) =>
              updateTask(t.index, { expected_answer: e.target.value, ai: false })
            }
          />
        </div>
      ))}

      <button className="btn wide" onClick={addTask}>
        + Добавить задание
      </button>

      <div style={{ height: 12 }} />
      <button
        className="btn primary wide"
        disabled={!canSubmit || saving}
        onClick={submit}
      >
        {saving ? "Сохраняю…" : "Создать работу"}
      </button>
    </div>
  );
}
