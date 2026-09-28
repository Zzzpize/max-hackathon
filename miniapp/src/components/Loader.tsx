export function Loader({ text = "Загрузка…" }: { text?: string }) {
  return (
    <div className="page" style={{ textAlign: "center", paddingTop: 32 }}>
      <div
        style={{
          width: 32,
          height: 32,
          border: "3px solid #e5e7eb",
          borderTopColor: "#2563eb",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
          margin: "0 auto 12px",
        }}
      />
      <div className="muted-text">{text}</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
