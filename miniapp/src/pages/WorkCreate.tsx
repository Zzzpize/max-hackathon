import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useTeacherId } from "../max/useTeacherId";

type TaskInput = { index: number; statement: string; expected_answer: string };

export function WorkCreate() {
  const teacherId = useTeacherId();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [grade, setGrade] = useState<number>(3);
  const [tasks, setTasks] = useState<TaskInput[]>([
    { index: 1, statement: "", expected_answer: "" },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        teacher_id: teacherId,
        title: title.trim(),
        subject: "math",
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

  return (
    <div className="page">
      <h1>Новая контрольная</h1>
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
        <label className="label">Класс</label>
        <select
          className="input"
          value={grade}
          onChange={(e) => setGrade(Number(e.target.value))}
        >
          <option value={2}>2 класс</option>
          <option value={3}>3 класс</option>
          <option value={4}>4 класс</option>
        </select>
      </div>

      <h2>Задания</h2>
      {tasks.map((t) => (
        <div key={t.index} className="card">
          <div className="row spread" style={{ marginBottom: 6 }}>
            <b>Задание {t.index}</b>
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
            onChange={(e) => updateTask(t.index, { statement: e.target.value })}
          />
          <div style={{ height: 6 }} />
          <label className="label">Эталонный ответ</label>
          <input
            className="input"
            placeholder="68"
            value={t.expected_answer}
            onChange={(e) =>
              updateTask(t.index, { expected_answer: e.target.value })
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
