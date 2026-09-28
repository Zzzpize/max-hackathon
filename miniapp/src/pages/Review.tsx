import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type SubmissionResult, type TaskCheck } from "../api/client";
import { Loader } from "../components/Loader";
import { maxBridge } from "../max/bridge";
import { useTeacherId } from "../max/useTeacherId";

function confidenceColor(c: number): string {
  if (c >= 0.9) return "#10b981";
  if (c >= 0.7) return "#eab308";
  return "#ef4444";
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div
      style={{
        height: 4,
        background: "#f1f5f9",
        borderRadius: 999,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: confidenceColor(value),
        }}
      />
    </div>
  );
}

function TaskCard({
  task,
  onToggle,
  onEditAnswer,
}: {
  task: TaskCheck;
  onToggle: () => void;
  onEditAnswer: (v: string) => void;
}) {
  const lowConfidence = task.confidence < 0.7;
  return (
    <div className={`card${lowConfidence ? " warn" : ""}`}>
      <div className="row spread" style={{ marginBottom: 8 }}>
        <div>
          <b>Задание {task.task_index}</b>
          {lowConfidence && (
            <span
              className="badge warn"
              style={{ marginLeft: 8 }}
            >
              проверь вручную
            </span>
          )}
        </div>
        <button
          onClick={onToggle}
          className="btn"
          style={{
            background: task.is_correct ? "#d1fae5" : "#fee2e2",
            color: task.is_correct ? "#065f46" : "#991b1b",
            padding: "6px 12px",
          }}
        >
          {task.is_correct ? "✓ верно" : "✗ ошибка"}
        </button>
      </div>

      <div style={{ marginBottom: 6 }}>
        <div className="label">Распознано у ученика</div>
        <input
          className="input"
          value={task.student_answer}
          onChange={(e) => onEditAnswer(e.target.value)}
          placeholder="ответ не распознан"
        />
      </div>

      <div className="row spread" style={{ marginBottom: 6 }}>
        <div>
          <span className="muted-text">Эталон: </span>
          <b>{task.expected_answer}</b>
        </div>
        <span className="muted-text" style={{ fontSize: 11 }}>
          уверенность {(task.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <ConfidenceBar value={task.confidence} />

      {task.explanation && (
        <p className="muted-text" style={{ marginTop: 8 }}>
          {task.explanation}
        </p>
      )}

      {task.reasoning_graph.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary className="muted-text" style={{ cursor: "pointer" }}>
            Ход решения ({task.reasoning_graph.length} шагов)
          </summary>
          <ol style={{ marginTop: 6, paddingLeft: 18 }}>
            {task.reasoning_graph.map((s, i) => (
              <li
                key={i}
                style={{ color: s.ok ? "#065f46" : "#991b1b" }}
              >
                {s.step}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

export function Review() {
  const { submissionId = "" } = useParams();
  const teacherId = useTeacherId();
  const navigate = useNavigate();
  const [data, setData] = useState<SubmissionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getSubmission(submissionId, teacherId)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [submissionId, teacherId]);

  const stats = useMemo(() => {
    if (!data) return null;
    const total = data.per_task.length;
    const correct = data.per_task.filter((t) => t.is_correct).length;
    const uncertain = data.per_task.filter((t) => t.confidence < 0.7).length;
    return { total, correct, uncertain };
  }, [data]);

  if (error) return <p className="page" style={{ color: "crimson" }}>{error}</p>;
  if (!data) return <Loader text="Загрузка результата…" />;

  const patchTask = (idx: number, patch: Partial<TaskCheck>) =>
    setData({
      ...data,
      per_task: data.per_task.map((t) =>
        t.task_index === idx ? { ...t, ...patch } : t
      ),
    });

  const acceptAll = () =>
    setData({
      ...data,
      per_task: data.per_task.map((t) => ({ ...t, is_correct: true })),
    });

  const confirm = async () => {
    setSaving(true);
    try {
      await api.reviewSubmission(
        submissionId,
        teacherId,
        data.per_task.map((t) => ({
          task_index: t.task_index,
          is_correct: t.is_correct,
        }))
      );
      maxBridge.hapticNotify("success");
      navigate("/");
    } catch (e) {
      setError(String(e));
      maxBridge.hapticNotify("error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="page">
        <h1>Проверка работы</h1>

        <div className="card">
          <div className="row spread">
            <div>
              <div className="label">Всего заданий</div>
              <b style={{ fontSize: 18 }}>
                {stats?.correct} / {stats?.total} верно
              </b>
            </div>
            <div>
              <div className="label">Балл</div>
              <b style={{ fontSize: 18 }}>{data.total_score}</b>
            </div>
            <div>
              <div className="label">Уверенность</div>
              <b
                style={{
                  fontSize: 18,
                  color: confidenceColor(data.confidence),
                }}
              >
                {(data.confidence * 100).toFixed(0)}%
              </b>
            </div>
          </div>
          {stats && stats.uncertain > 0 && (
            <p className="muted-text" style={{ marginTop: 8 }}>
              {stats.uncertain} {stats.uncertain === 1 ? "задание" : "заданий"} с
              низкой уверенностью — проверь вручную.
            </p>
          )}
        </div>

        <div className="row" style={{ margin: "8px 0" }}>
          <button className="btn subtle" onClick={acceptAll}>
            Принять все верными
          </button>
        </div>

        {data.per_task.map((t) => (
          <TaskCard
            key={t.task_index}
            task={t}
            onToggle={() => patchTask(t.task_index, { is_correct: !t.is_correct })}
            onEditAnswer={(v) => patchTask(t.task_index, { student_answer: v })}
          />
        ))}
      </div>

      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          padding: 12,
          background: "#f5f7fa",
          borderTop: "1px solid rgba(0,0,0,0.06)",
          boxShadow: "0 -1px 3px rgba(0,0,0,0.04)",
        }}
      >
        <button
          className="btn primary wide"
          onClick={confirm}
          disabled={saving}
        >
          {saving ? "Сохраняю…" : "Подтвердить"}
        </button>
      </div>
    </>
  );
}
