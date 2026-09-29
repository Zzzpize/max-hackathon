import { useState } from "react";
import { useNavigate } from "react-router-dom";
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

const PLACEHOLDER = `3-А класс, 30 человек. Программа на 34 недели с 1 сентября.
Слабые в дробях и десятичных, сильные в устном счёте.
Хочу больше геометрии к концу года. Убрать вероятности — они в 5 классе.`;

export function RoadmapCreate() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState<SubjectId>("math");
  const [grade, setGrade] = useState<number>(3);
  const [prompt, setPrompt] = useState("");
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

  const canSubmit = prompt.trim().length >= 10;

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await api.createRoadmap({
        title: title.trim() || undefined,
        subject,
        grade,
        prompt: prompt.trim(),
      });
      navigate(`/roadmaps/${r.id}`, { replace: true });
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  };

  if (saving) return <Loader text="Генерирую план… это займёт ~30 секунд" />;

  return (
    <div className="page">
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <label className="label">Название (необязательно)</label>
        <input
          className="input"
          placeholder="AI подберёт, если оставить пустым"
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
      </div>

      <div className="card">
        <label className="label">Опишите план в свободной форме</label>
        <textarea
          className="textarea"
          rows={8}
          placeholder={PLACEHOLDER}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <div className="muted-text" style={{ marginTop: 6 }}>
          Пиши что важно: сколько недель, слабые/сильные темы, что убрать или
          добавить, особенности класса. От 10 до 2000 символов.
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
