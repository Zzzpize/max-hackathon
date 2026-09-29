import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Homework } from "../../api/client";
import { Loader } from "../../components/Loader";
import { subjectLabel } from "../../subjects";

export function HomeworkView() {
  const { homeworkId } = useParams<{ homeworkId: string }>();
  const navigate = useNavigate();
  const [hw, setHw] = useState<Homework | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [showAnswers, setShowAnswers] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!homeworkId) return;
    api
      .getHomework(homeworkId)
      .then(setHw)
      .catch((e) => setError(String(e)));
  }, [homeworkId]);

  const remove = async () => {
    if (!homeworkId) return;
    if (!window.confirm("Удалить домашку?")) return;
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
    try {
      const updated = await api.regenerateHomework(homeworkId, extra);
      setHw(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setRegenerating(false);
    }
  };

  if (!hw && !error) return <Loader text="Загружаю…" />;
  if (error) return <div className="page"><p style={{ color: "crimson" }}>{error}</p></div>;
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

      {menuOpen && (
        <div className="card">
          <button
            className="btn wide"
            onClick={regenerate}
            disabled={regenerating}
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
          <a
            href={api.homeworkExportUrl(hw.id, "txt")}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ⬇ Скачать TXT
          </a>
          <a
            href={api.homeworkExportUrl(hw.id, "pdf")}
            className="btn wide"
            style={{ display: "block", textAlign: "center", marginBottom: 6 }}
          >
            ⬇ Скачать PDF
          </a>
          <button className="btn danger wide" onClick={remove}>
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
