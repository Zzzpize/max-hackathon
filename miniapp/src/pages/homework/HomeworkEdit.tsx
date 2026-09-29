import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Homework, type HomeworkTask } from "../../api/client";
import { Loader } from "../../components/Loader";

export function HomeworkEdit() {
  const { homeworkId } = useParams<{ homeworkId: string }>();
  const navigate = useNavigate();
  const [hw, setHw] = useState<Homework | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [tasks, setTasks] = useState<HomeworkTask[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!homeworkId) return;
    api
      .getHomework(homeworkId)
      .then((h) => {
        setHw(h);
        setTitle(h.title);
        setNotes(h.notes ?? "");
        setTasks(h.tasks);
      })
      .catch((e) => setError(String(e)));
  }, [homeworkId]);

  const updateTask = (index: number, patch: Partial<HomeworkTask>) =>
    setTasks((prev) =>
      prev.map((t) => (t.index === index ? { ...t, ...patch } : t))
    );

  const removeTask = (index: number) =>
    setTasks((prev) =>
      prev
        .filter((t) => t.index !== index)
        .map((t, i) => ({ ...t, index: i + 1 }))
    );

  const addTask = () =>
    setTasks((prev) => [
      ...prev,
      { index: prev.length + 1, statement: "", expected_answer: "" },
    ]);

  const canSave =
    title.trim().length > 0 &&
    tasks.length > 0 &&
    tasks.every((t) => t.statement.trim() && t.expected_answer.trim());

  const save = async () => {
    if (!homeworkId) return;
    setSaving(true);
    setError(null);
    try {
      await api.patchHomework(homeworkId, {
        title: title.trim(),
        notes: notes.trim() || null,
        tasks,
      });
      navigate(`/homework/${homeworkId}`, { replace: true });
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  };

  if (!hw && !error) return <Loader text="Загружаю…" />;
  if (error && !hw)
    return <div className="page"><p style={{ color: "crimson" }}>{error}</p></div>;
  if (!hw) return null;

  return (
    <div className="page">
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <label className="label">Название</label>
        <input
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div style={{ height: 8 }} />
        <label className="label">Заметки для себя</label>
        <textarea
          className="textarea"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
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
            value={t.statement}
            onChange={(e) => updateTask(t.index, { statement: e.target.value })}
          />
          <div style={{ height: 6 }} />
          <label className="label">Эталонный ответ</label>
          <input
            className="input"
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
        onClick={save}
        disabled={saving || !canSave}
      >
        {saving ? "Сохраняю…" : "Сохранить"}
      </button>
    </div>
  );
}
