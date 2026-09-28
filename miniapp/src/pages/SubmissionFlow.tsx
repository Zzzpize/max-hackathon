import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api,
  type Student,
  type TeacherState,
  type WorkTemplate,
} from "../api/client";
import { Loader } from "../components/Loader";

export function SubmissionFlow() {
  const navigate = useNavigate();
  const [state, setState] = useState<TeacherState | null>(null);
  const [work, setWork] = useState<WorkTemplate | null>(null);
  const [student, setStudent] = useState<Student | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await api.getState();
        setState(s);
        const [ws, ss] = await Promise.all([
          api.listWorks(),
          api.listStudents(),
        ]);
        setWork(ws.find((w) => w.id === s.current_work_id) ?? null);
        setStudent(ss.find((st) => st.id === s.current_student_id) ?? null);
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  const addPhotos = (files: FileList | null) => {
    if (!files) return;
    setPhotos((prev) => [...prev, ...Array.from(files)].slice(0, 4));
  };
  const removePhoto = (idx: number) =>
    setPhotos((prev) => prev.filter((_, i) => i !== idx));

  const canSubmit = work && student && photos.length > 0;

  const submit = async () => {
    if (!work || !student || photos.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const sub = await api.submitWork({
        workId: work.id,
        studentId: student.id,
        photos,
      });
      navigate(`/review/${sub.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
    }
  };

  if (!state) return <Loader />;

  return (
    <div className="page">
      <h1>Загрузить работу</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="card">
        <div className="row spread">
          <div>
            <div className="label">Работа</div>
            <b>{work?.title ?? <span className="muted-text">не выбрана</span>}</b>
          </div>
          <Link to="/pick/work" className="btn subtle">
            Сменить
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="row spread">
          <div>
            <div className="label">Ученик</div>
            <b>
              {student ? (
                `${student.display_name} · ${student.class_id}`
              ) : (
                <span className="muted-text">не выбран</span>
              )}
            </b>
          </div>
          <Link to="/pick/student" className="btn subtle">
            Сменить
          </Link>
        </div>
      </div>

      <h2>Фото работы <span className="muted-text">· до 4 страниц</span></h2>
      <div className="row wrap" style={{ gap: 8 }}>
        {photos.map((p, idx) => (
          <div key={idx} style={{ position: "relative" }}>
            <img
              src={URL.createObjectURL(p)}
              alt=""
              style={{
                width: 96,
                height: 96,
                objectFit: "cover",
                borderRadius: 10,
              }}
            />
            <button
              className="btn subtle danger"
              onClick={() => removePhoto(idx)}
              style={{
                position: "absolute",
                top: -6,
                right: -6,
                padding: "2px 6px",
                fontSize: 11,
                background: "#fee2e2",
                borderRadius: 999,
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div style={{ height: 12 }} />
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        multiple
        onChange={(e) => addPhotos(e.target.files)}
        style={{ display: "none" }}
      />
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(e) => addPhotos(e.target.files)}
        style={{ display: "none" }}
      />
      <div className="row" style={{ gap: 8 }}>
        <button
          className="btn wide"
          onClick={() => fileRef.current?.click()}
          disabled={photos.length >= 4}
          style={{ flex: 1 }}
        >
          🖼 Из галереи
        </button>
        <button
          className="btn wide"
          onClick={() => cameraRef.current?.click()}
          disabled={photos.length >= 4}
          style={{ flex: 1 }}
        >
          📷 Камера
        </button>
      </div>
      {photos.length > 0 && (
        <p className="muted-text" style={{ textAlign: "center", marginTop: 6 }}>
          {photos.length}/4 фото
        </p>
      )}

      <div style={{ height: 12 }} />
      <button
        className="btn primary wide"
        onClick={submit}
        disabled={!canSubmit || uploading}
      >
        {uploading ? "Отправляю…" : "Отправить на проверку"}
      </button>
    </div>
  );
}
