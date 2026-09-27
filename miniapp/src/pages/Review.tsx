import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type SubmissionResult } from "../api/client";
import { useTeacherId } from "../max/useTeacherId";

export function Review() {
  const { submissionId = "" } = useParams();
  const teacherId = useTeacherId();
  const [data, setData] = useState<SubmissionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getSubmission(submissionId, teacherId)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [submissionId, teacherId]);

  if (error) return <p style={{ padding: 16, color: "crimson" }}>{error}</p>;
  if (!data) return <p style={{ padding: 16 }}>Загрузка…</p>;

  const toggleTask = (idx: number) => {
    setData({
      ...data,
      per_task: data.per_task.map((t) =>
        t.task_index === idx ? { ...t, is_correct: !t.is_correct } : t
      ),
    });
  };

  const confirm = async () => {
    setSaving(true);
    try {
      await api.reviewSubmission(
        submissionId,
        teacherId,
        data.per_task.map((t) => ({ task_index: t.task_index, is_correct: t.is_correct }))
      );
      history.back();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h1 style={{ fontSize: 20 }}>Проверка работы</h1>
      <p style={{ color: "#666" }}>
        Уверенность модели: {(data.confidence * 100).toFixed(0)}% · Балл:{" "}
        {data.total_score}
      </p>

      {data.per_task.map((t) => (
        <div
          key={t.task_index}
          style={{
            background: "#fff",
            padding: 12,
            marginBottom: 8,
            borderRadius: 12,
            border: t.confidence < 0.7 ? "1px solid #ffb020" : "none",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <strong>Задание {t.task_index}</strong>
            <button onClick={() => toggleTask(t.task_index)}>
              {t.is_correct ? "✓ верно" : "✗ ошибка"}
            </button>
          </div>
          <p style={{ margin: "4px 0" }}>
            Ответ ученика: <b>{t.student_answer || "—"}</b> ·
            эталон: <b>{t.expected_answer}</b>
          </p>
          {t.explanation && <p style={{ color: "#444" }}>{t.explanation}</p>}
          {t.confidence < 0.7 && (
            <p style={{ color: "#a06000", fontSize: 12 }}>
              Низкая уверенность распознавания — проверь вручную.
            </p>
          )}
        </div>
      ))}

      <button
        onClick={confirm}
        disabled={saving}
        style={{
          width: "100%",
          padding: 14,
          borderRadius: 12,
          border: "none",
          background: "#2563eb",
          color: "#fff",
          fontSize: 16,
        }}
      >
        {saving ? "Сохраняю…" : "Подтвердить"}
      </button>
    </div>
  );
}
