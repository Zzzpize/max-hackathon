import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export function StudentCreate() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [classId, setClassId] = useState("3-А");
  const [grade, setGrade] = useState(3);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = name.trim().length > 0 && classId.trim().length > 0;

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.createStudent({
        class_id: classId.trim(),
        display_name: name.trim(),
        grade,
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
      <h1>Новый ученик</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <label className="label">Имя (или инициалы)</label>
        <input
          className="input"
          placeholder="Иванов П."
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div style={{ height: 8 }} />
        <label className="label">Класс</label>
        <input
          className="input"
          placeholder="3-А"
          value={classId}
          onChange={(e) => setClassId(e.target.value)}
        />
        <div style={{ height: 8 }} />
        <label className="label">Ступень</label>
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

      <p className="muted-text">
        Имя видишь только ты. В базе хранится как есть, без привязки к
        внешним данным.
      </p>

      <button
        className="btn primary wide"
        disabled={!canSubmit || saving}
        onClick={submit}
      >
        {saving ? "Сохраняю…" : "Добавить ученика"}
      </button>
    </div>
  );
}
