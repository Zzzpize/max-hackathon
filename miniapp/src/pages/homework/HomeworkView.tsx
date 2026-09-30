import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadAuthorized, type Homework } from "../../api/client";
import { Loader } from "../../components/Loader";
import { subjectLabel } from "../../subjects";

function sanitizeFilename(name: string): string {
  const cleaned = name.replace(/[\\/:*?"<>|]+/g, "").trim();
  return cleaned || "homework";
}

export function HomeworkView() {
  const { homeworkId } = useParams<{ homeworkId: string }>();
  const navigate = useNavigate();
  const [hw, setHw] = useState<Homework | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [showAnswers, setShowAnswers] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!homeworkId) return;
    api
      .getHomework(homeworkId)
      .then(setHw)
      .catch((e) => setError(String(e)));
  }, [homeworkId]);

  const remove = async () => {
    if (!homeworkId) return;
    if (!window.confirm("Удалить домашнее задание?")) return;
    try {
      await api.deleteHomework(homeworkId);
      navigate("/homework", { replace: true });
    } catch (e) {
      setError(String(e));
    }
  };

  const regenerate = async () => {
    if (!homeworkId) return;
    const extra =
      window.prompt("Что поправить? (можно пусто — просто перегенерирую)") ?? "";
    setRegenerating(true);
    setError(null);
    try {
      const updated = await api.regenerateHomework(homeworkId, extra);
      setHw(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setRegenerating(false);
    }
  };

  const download = async (format: "txt" | "pdf") => {
    if (!hw) return;
    setBusy(format);
    setError(null);
    try {
      const filename = `${sanitizeFilename(hw.title)}.${format}`;
      await downloadAuthorized(`/homework/${hw.id}/export?format=${format}`, filename);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const sendToCheck = async () => {
    if (!hw) return;
    if (!window.confirm(`Создать контрольную «${hw.title}» из этого задания? Задачи и эталонные ответы скопируются во вкладку «Проверка».`)) return;
    setBusy("send");
    setError(null);
    try {
      const work = await api.createWork({
        title: hw.title,
        subject: hw.subject,
        grade: hw.grade,
        tasks: hw.tasks.map((t) => ({
          index: t.index,
          statement: t.statement,
          expected_answer: t.expected_answer,
        })),
      });
      await api.setState({ current_work_id: work.id });
      navigate("/");
    } catch (e) {
      setError(String(e));
      setBusy(null);
    }
  };

  if (!hw && !error) return <Loader text="Загружаю…" />;
  if (error && !hw) return <div className="page"><p style={{ color: "crimson" }}>{error}</p></div>;
  if (!hw) return null;

  return (
    <div className="page">
      <div className="row spread" style={{ marginBottom: 8 }}>
        <div>
          <h1 style={{ margin: 0 }}>{hw.title}</h1>
          <div className="muted-text" style={{ marginTop: 4 }}>
            {subjectLabel(hw.subject)} · {hw.grade} класс · {hw.topic}
          </div>
        </div>
        <button
          className="btn subtle"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Меню"
          style={{ fontSize: 20 }}
        >
          ⋮
        </button>
      </div>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {menuOpen && (
        <div className="card">
          <button
            className="btn primary wide"
            onClick={sendToCheck}
            disabled={busy !== null}
            style={{ marginBottom: 6 }}
          >
            {busy === "send" ? "Создаю…" : "↗ Отправить в проверку"}
          </button>
          <button
            className="btn wide"
            onClick={regenerate}
            disabled={regenerating || busy !== null}
            style={{ marginBottom: 6 }}
          >
            {regenerating ? "Генерирую…" : "🔄 Перегенерировать"}
          </button>
          <Link
            to={`/homework/${hw.id}/edit`}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ✏️ Редактировать
          </Link>
          <button
            className="btn wide"
            onClick={() => download("txt")}
            disabled={busy !== null}
            style={{ marginBottom: 6 }}
          >
            {busy === "txt" ? "Скачиваю…" : "⬇ Скачать TXT"}
          </button>
          <button
            className="btn wide"
            onClick={() => download("pdf")}
            disabled={busy !== null}
            style={{ marginBottom: 6 }}
          >
            {busy === "pdf" ? "Скачиваю…" : "⬇ Скачать PDF"}
          </button>
          <button className="btn danger wide" onClick={remove} disabled={busy !== null}>
            Удалить
          </button>
        </div>
      )}

      <h2>Задания</h2>
      {hw.tasks.map((t) => (
        <div key={t.index} className="card">
          <b>Задание {t.index}</b>
          <div style={{ marginTop: 4, whiteSpace: "pre-wrap" }}>{t.statement}</div>
          {showAnswers && (
            <div style={{ marginTop: 8 }}>
              <div className="label">Ответ</div>
              <div>{t.expected_answer}</div>
            </div>
          )}
        </div>
      ))}

      <button
        className="btn wide"
        onClick={() => setShowAnswers((v) => !v)}
        style={{ marginTop: 12 }}
      >
        {showAnswers ? "Скрыть ответы" : "Показать ответы"}
      </button>
    </div>
  );
}
