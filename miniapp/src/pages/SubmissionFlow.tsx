import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Student, type WorkTemplate } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { Loader } from "../components/Loader";
import { maxBridge } from "../max/bridge";

const MAX_PHOTOS_PER_STUDENT = 10;

type StudentSlot = {
  student: Student;
  photos: File[];
};

export function SubmissionFlow() {
  const navigate = useNavigate();
  const [work, setWork] = useState<WorkTemplate | null>(null);
  const [allStudents, setAllStudents] = useState<Student[]>([]);
  const [selected, setSelected] = useState<Record<string, StudentSlot>>({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<string, string[]>>({});
  useEffect(() => {
    (async () => {
      try {
        const state = await api.getState();
        if (!state.current_work_id) {
          setError("Сначала выбери работу.");
          return;
        }
        const [w, students] = await Promise.all([
          api.getWork(state.current_work_id),
          api.listStudents(),
        ]);
        setWork(w);
        setAllStudents(students);
        if (state.current_student_id) {
          const preselected = students.find((s) => s.id === state.current_student_id);
          if (preselected) {
            setSelected({ [preselected.id]: { student: preselected, photos: [] } });
          }
        }
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const grouped = useMemo(() => {
    return allStudents.reduce<Record<string, Student[]>>((acc, s) => {
      (acc[s.class_id] ??= []).push(s);
      return acc;
    }, {});
  }, [allStudents]);

  const toggleStudent = (student: Student) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (next[student.id]) delete next[student.id];
      else next[student.id] = { student, photos: [] };
      return next;
    });
  };

  const selectAllInClass = (classId: string) => {
    const students = grouped[classId] ?? [];
    setSelected((prev) => {
      const next = { ...prev };
      for (const s of students) if (!next[s.id]) next[s.id] = { student: s, photos: [] };
      return next;
    });
  };

  const addPhotosTo = (studentId: string, files: FileList | null) => {
    if (!files || files.length === 0) return;
    const list = Array.from(files);
    setSelected((prev) => {
      const slot = prev[studentId];
      if (!slot) return prev;
      const merged = [...slot.photos, ...list].slice(0, MAX_PHOTOS_PER_STUDENT);
      return { ...prev, [studentId]: { ...slot, photos: merged } };
    });

    list.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const url = String(reader.result || "");
        setPreviews((prev) => ({
          ...prev,
          [studentId]: [...(prev[studentId] ?? []), url].slice(
            0,
            MAX_PHOTOS_PER_STUDENT
          ),
        }));
      };
      reader.readAsDataURL(file);
    });
  };

  const removePhoto = (studentId: string, idx: number) => {
    setSelected((prev) => {
      const slot = prev[studentId];
      if (!slot) return prev;
      return {
        ...prev,
        [studentId]: {
          ...slot,
          photos: slot.photos.filter((_, i) => i !== idx),
        },
      };
    });
    setPreviews((prev) => ({
      ...prev,
      [studentId]: (prev[studentId] ?? []).filter((_, i) => i !== idx),
    }));
  };

  const selectedList = Object.values(selected);
  const readyCount = selectedList.filter((s) => s.photos.length > 0).length;
  const totalPhotos = selectedList.reduce((sum, s) => sum + s.photos.length, 0);
  const canSubmit = work && readyCount > 0 && readyCount === selectedList.length;

  const submit = async () => {
    if (!work) return;
    setUploading(true);
    setError(null);
    setProgress({ done: 0, total: selectedList.length });
    try {
      const results = await api.submitBatch({
        workId: work.id,
        students: selectedList.map((s) => ({
          studentId: s.student.id,
          photos: s.photos,
        })),
        concurrency: 5,
        onProgress: (done, total) => setProgress({ done, total }),
      });
      const failed = results.filter((r) => r.result instanceof Error);
      if (failed.length > 0) {
        setError(
          `Отправлено: ${results.length - failed.length}/${results.length}. ` +
            `Не получилось у ${failed.length} — попробуй ещё раз.`
        );
        maxBridge.hapticNotify("warning");
      } else {
        maxBridge.hapticNotify("success");
        navigate("/");
      }
    } catch (e) {
      setError(String(e));
      maxBridge.hapticNotify("error");
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <Loader />;

  if (!work) {
    return (
      <div className="page">
        <EmptyState
          title="Работа не выбрана"
          hint="Вернись в главную и выбери работу."
          action={
            <Link to="/pick/work" className="btn primary">
              Выбрать работу
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <>
      <div className="page">
        {error && <p style={{ color: "crimson" }}>{error}</p>}

        <div className="card">
          <div className="label">Работа</div>
          <b>{work.title}</b>
        </div>

        <h2>
          Ученики <span className="muted-text">· {selectedList.length} выбрано</span>
        </h2>
        {allStudents.length === 0 && (
          <EmptyState
            title="Нет учеников"
            hint="Добавь хотя бы одного, чтобы отправить работу."
            action={
              <Link to="/students/new" className="btn primary">
                Добавить
              </Link>
            }
          />
        )}

        {Object.entries(grouped).map(([classId, list]) => (
          <div key={classId}>
            <div className="row spread" style={{ margin: "12px 0 6px" }}>
              <b>{classId}</b>
              <button
                className="btn subtle"
                onClick={() => selectAllInClass(classId)}
              >
                Выбрать всех
              </button>
            </div>
            {list.map((s) => {
              const slot = selected[s.id];
              const active = Boolean(slot);
              return (
                <div key={s.id} className="card" style={{ padding: 10 }}>
                  <label
                    className="row spread"
                    style={{ cursor: "pointer", gap: 10 }}
                  >
                    <div className="row" style={{ gap: 8 }}>
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => toggleStudent(s)}
                        style={{ width: 18, height: 18 }}
                      />
                      <span>{s.display_name}</span>
                    </div>
                    {slot && (
                      <span
                        className="badge"
                        style={
                          slot.photos.length > 0
                            ? { background: "#d1fae5", color: "#065f46" }
                            : { background: "#fee2e2", color: "#991b1b" }
                        }
                      >
                        {slot.photos.length}/{MAX_PHOTOS_PER_STUDENT} фото
                      </span>
                    )}
                  </label>

                  {active && (
                    <div style={{ marginTop: 8 }}>
                      {slot.photos.length > 0 && (
                        <div
                          className="row wrap"
                          style={{ gap: 6, marginBottom: 8 }}
                        >
                          {slot.photos.map((p, idx) => {
                            const previewUrl = previews[s.id]?.[idx];
                            return (
                            <div key={idx} style={{ position: "relative" }}>
                              {previewUrl ? (
                                <img
                                  src={previewUrl}
                                  alt=""
                                  style={{
                                    width: 60,
                                    height: 60,
                                    objectFit: "cover",
                                    borderRadius: 8,
                                  }}
                                />
                              ) : (
                                <div
                                  style={{
                                    width: 60,
                                    height: 60,
                                    borderRadius: 8,
                                    background: "#e5e7eb",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: 10,
                                    color: "#6b7280",
                                    textAlign: "center",
                                    padding: 4,
                                  }}
                                >
                                  {p.name.slice(0, 12)}
                                </div>
                              )}
                              <button
                                className="btn subtle danger"
                                onClick={() => removePhoto(s.id, idx)}
                                style={{
                                  position: "absolute",
                                  top: -6,
                                  right: -6,
                                  padding: "1px 5px",
                                  fontSize: 10,
                                  background: "#fee2e2",
                                  borderRadius: 999,
                                }}
                              >
                                ✕
                              </button>
                            </div>
                            );
                          })}
                        </div>
                      )}
                      <div className="row" style={{ gap: 6 }}>
                        <label
                          className="btn"
                          aria-disabled={slot.photos.length >= MAX_PHOTOS_PER_STUDENT}
                          style={{
                            flex: 1,
                            padding: 8,
                            fontSize: 13,
                            textAlign: "center",
                            cursor:
                              slot.photos.length >= MAX_PHOTOS_PER_STUDENT
                                ? "not-allowed"
                                : "pointer",
                            opacity:
                              slot.photos.length >= MAX_PHOTOS_PER_STUDENT ? 0.5 : 1,
                          }}
                        >
                          🖼 Из галереи
                          <input
                            type="file"
                            accept="image/*"
                            multiple
                            disabled={slot.photos.length >= MAX_PHOTOS_PER_STUDENT}
                            style={{ display: "none" }}
                            onChange={(e) => {
                              addPhotosTo(s.id, e.target.files);
                              e.target.value = "";
                            }}
                          />
                        </label>
                        <label
                          className="btn"
                          aria-disabled={slot.photos.length >= MAX_PHOTOS_PER_STUDENT}
                          style={{
                            flex: 1,
                            padding: 8,
                            fontSize: 13,
                            textAlign: "center",
                            cursor:
                              slot.photos.length >= MAX_PHOTOS_PER_STUDENT
                                ? "not-allowed"
                                : "pointer",
                            opacity:
                              slot.photos.length >= MAX_PHOTOS_PER_STUDENT ? 0.5 : 1,
                          }}
                        >
                          📷 Камера
                          <input
                            type="file"
                            accept="image/*"
                            capture="environment"
                            disabled={slot.photos.length >= MAX_PHOTOS_PER_STUDENT}
                            style={{ display: "none" }}
                            onChange={(e) => {
                              addPhotosTo(s.id, e.target.files);
                              e.target.value = "";
                            }}
                          />
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
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
        }}
      >
        {uploading && (
          <div className="muted-text" style={{ marginBottom: 8, fontSize: 12 }}>
            Отправляю {progress.done}/{progress.total}…
          </div>
        )}
        <button
          className="btn primary wide"
          onClick={submit}
          disabled={!canSubmit || uploading}
        >
          {uploading
            ? "Отправляю…"
            : selectedList.length === 0
            ? "Выбери учеников"
            : readyCount < selectedList.length
            ? `Добавь фото у ${selectedList.length - readyCount} учеников`
            : `Отправить ${selectedList.length} работ · ${totalPhotos} фото`}
        </button>
      </div>
    </>
  );
}
