import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  api,
  photoUrl,
  type SubmissionResult,
  type TaskCheck,
} from "../api/client";
import { Loader } from "../components/Loader";
import { maxBridge } from "../max/bridge";

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

function PhotoViewer({
  photos,
  tasks,
  highlightedTaskIndex,
  onClose,
}: {
  photos: string[];
  tasks: TaskCheck[];
  highlightedTaskIndex: number | null;
  onClose: () => void;
}) {
  const [activePhoto, setActivePhoto] = useState(() => {
    if (highlightedTaskIndex === null) return 0;
    const task = tasks.find((t) => t.task_index === highlightedTaskIndex);
    return task?.photo_boxes[0]?.photo_index ?? 0;
  });

  const boxesForPhoto = tasks
    .flatMap((t) =>
      t.photo_boxes.map((b) => ({ ...b, task_index: t.task_index, is_correct: t.is_correct }))
    )
    .filter((b) => b.photo_index === activePhoto);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.92)",
        zIndex: 100,
        display: "flex",
        flexDirection: "column",
      }}
      onClick={onClose}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: 12,
          color: "#fff",
        }}
      >
        <span>
          Фото {activePhoto + 1} / {photos.length}
        </span>
        <button
          className="btn"
          onClick={onClose}
          style={{ background: "rgba(255,255,255,0.15)", color: "#fff" }}
        >
          ✕
        </button>
      </div>
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 12,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ position: "relative", maxWidth: "100%", maxHeight: "100%" }}>
          <img
            src={photoUrl(photos[activePhoto])}
            alt=""
            style={{ maxWidth: "100%", maxHeight: "70vh", display: "block" }}
          />
          {boxesForPhoto.map((b, i) => {
            const highlighted =
              highlightedTaskIndex === null ||
              b.task_index === highlightedTaskIndex;
            const color = b.is_correct ? "#10b981" : "#ef4444";
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: `${b.x * 100}%`,
                  top: `${b.y * 100}%`,
                  width: `${b.w * 100}%`,
                  height: `${b.h * 100}%`,
                  border: `2px solid ${color}`,
                  background: highlighted ? `${color}30` : "transparent",
                  opacity: highlighted ? 1 : 0.35,
                  borderRadius: 4,
                  transition: "opacity 0.15s",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    top: -18,
                    left: 0,
                    background: color,
                    color: "#fff",
                    fontSize: 11,
                    padding: "1px 5px",
                    borderRadius: 3,
                  }}
                >
                  #{b.task_index}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      {photos.length > 1 && (
        <div
          style={{
            display: "flex",
            gap: 6,
            padding: 12,
            overflowX: "auto",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {photos.map((p, i) => (
            <img
              key={i}
              src={photoUrl(p)}
              alt=""
              onClick={() => setActivePhoto(i)}
              style={{
                width: 56,
                height: 56,
                objectFit: "cover",
                borderRadius: 6,
                border:
                  i === activePhoto ? "2px solid #fff" : "2px solid transparent",
                opacity: i === activePhoto ? 1 : 0.7,
                cursor: "pointer",
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TaskCard({
  task,
  onToggle,
  onEditAnswer,
  onShowOnPhoto,
}: {
  task: TaskCheck;
  onToggle: () => void;
  onEditAnswer: (v: string) => void;
  onShowOnPhoto: () => void;
}) {
  const lowConfidence = task.confidence < 0.7;
  const hasBoxes = task.photo_boxes.length > 0;
  return (
    <div className={`card${lowConfidence ? " warn" : ""}`}>
      <div className="row spread" style={{ marginBottom: 8 }}>
        <div>
          <b>Задание {task.task_index}</b>
          {lowConfidence && (
            <span className="badge warn" style={{ marginLeft: 8 }}>
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

      {hasBoxes && (
        <button
          className="btn subtle"
          onClick={onShowOnPhoto}
          style={{ marginTop: 8, padding: "6px 10px", fontSize: 12 }}
        >
          🔍 Показать на фото
        </button>
      )}

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
              <li key={i} style={{ color: s.ok ? "#065f46" : "#991b1b" }}>
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
  const navigate = useNavigate();
  const [data, setData] = useState<SubmissionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [highlightedTask, setHighlightedTask] = useState<number | null>(null);

  useEffect(() => {
    api
      .getSubmission(submissionId)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [submissionId]);

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

  const openViewer = (taskIndex: number | null) => {
    setHighlightedTask(taskIndex);
    setViewerOpen(true);
  };

  return (
    <>
      <div className="page">
        <h1>Проверка работы</h1>

        {data.photos.length > 0 && (
          <div
            style={{
              display: "flex",
              gap: 6,
              overflowX: "auto",
              margin: "0 -16px 12px",
              padding: "0 16px",
            }}
          >
            {data.photos.map((p, i) => (
              <img
                key={i}
                src={photoUrl(p)}
                alt={`Фото ${i + 1}`}
                onClick={() => openViewer(null)}
                style={{
                  width: 96,
                  height: 96,
                  objectFit: "cover",
                  borderRadius: 8,
                  flexShrink: 0,
                  cursor: "pointer",
                  border: "1px solid rgba(0,0,0,0.08)",
                }}
              />
            ))}
          </div>
        )}

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
            onShowOnPhoto={() => openViewer(t.task_index)}
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

      {viewerOpen && (
        <PhotoViewer
          photos={data.photos}
          tasks={data.per_task}
          highlightedTaskIndex={highlightedTask}
          onClose={() => setViewerOpen(false)}
        />
      )}
    </>
  );
}
