import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../../api/client";
import { Loader } from "../../components/Loader";
import {
  ALL_GRADES,
  firstSubjectFor,
  nearestGradeFor,
  SUBJECTS,
  subjectOptionLabel,
  subjectsForGrade,
  type SubjectId,
} from "../../subjects";

export function HomeworkCreate() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const prefillSubject = params.get("subject") as SubjectId | null;
  const prefillGrade = Number(params.get("grade")) || 0;
  const prefillTopic = params.get("topic") ?? "";

  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState<SubjectId>(
    prefillSubject && SUBJECTS.some((s) => s.id === prefillSubject) ? prefillSubject : "math"
  );
  const [grade, setGrade] = useState<number>(
    prefillGrade >= 1 && prefillGrade <= 11 ? prefillGrade : 3
  );
  const [topic, setTopic] = useState(prefillTopic);
  const [nTasks, setNTasks] = useState<number>(10);
  const [promptText, setPromptText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changeSubject = (next: SubjectId) => {
    setSubject(next);
    setGrade(nearestGradeFor(next, grade));
  };

  const changeGrade = (next: number) => {
    setGrade(next);
    if (!subjectsForGrade(next).some((s) => s.id === subject)) {
      setSubject(firstSubjectFor(next));
    }
  };

  const canSubmit =
    topic.trim().length > 0 &&
    promptText.trim().length >= 5 &&
    nTasks >= 1 &&
    nTasks <= 30;

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const h = await api.createHomework({
        title: title.trim() || undefined,
        subject,
        grade,
        topic: topic.trim(),
        n_tasks: nTasks,
        prompt: promptText.trim(),
      });
      navigate(`/homework/${h.id}`, { replace: true });
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  };

  if (saving) return <Loader text="Генерирую задачи…" />;

  return (
    <div className="page">
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <label className="label">Название (необязательно)</label>
        <input
          className="input"
          placeholder="Домашнее задание на 12.10: дроби"
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
          {SUBJECTS.map((s) => (
            <option key={s.id} value={s.id}>
              {subjectOptionLabel(s)}
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
          {ALL_GRADES.map((g) => (
            <option key={g} value={g}>
              {g} класс
            </option>
          ))}
        </select>
        <div style={{ height: 8 }} />
        <label className="label">Тема</label>
        <input
          className="input"
          placeholder="Сложение обыкновенных дробей"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
      </div>

      <div className="card">
        <label className="label">Сколько задач: {nTasks}</label>
        <input
          type="range"
          min={1}
          max={30}
          value={nTasks}
          onChange={(e) => setNTasks(Number(e.target.value))}
          style={{ width: "100%" }}
        />
      </div>

      <div className="card">
        <label className="label">Дополнительный контекст</label>
        <textarea
          className="textarea"
          rows={5}
          placeholder="Например: без дробей больше 1, с одной задачей на смекалку, средняя сложность"
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
        />
        <div className="muted-text" style={{ marginTop: 6 }}>
          От 5 до 2000 символов. Чем конкретнее — тем ближе к тому, что нужно.
        </div>
      </div>

      <button
        className="btn primary wide"
        disabled={!canSubmit}
        onClick={submit}
      >
        Сгенерировать
      </button>
    </div>
  );
}
