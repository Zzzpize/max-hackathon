import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { maxBridge } from "./max/bridge";
import { Dashboard } from "./pages/Dashboard";
import { Inbox } from "./pages/Inbox";
import { Review } from "./pages/Review";
import { StudentProfile } from "./pages/StudentProfile";

function StartParamRouter() {
  const navigate = useNavigate();

  useEffect(() => {
    const param = maxBridge.getStartParam();
    if (!param) return;
    const [kind, id] = param.split(":");
    if (kind === "submission" && id) navigate(`/review/${id}`, { replace: true });
    else if (kind === "student" && id) navigate(`/student/${id}`, { replace: true });
    else if (kind === "class" && id) navigate(`/dashboard/${id}`, { replace: true });
  }, [navigate]);

  return null;
}

export function App() {
  return (
    <>
      <StartParamRouter />
      <Routes>
        <Route path="/" element={<Navigate to="/inbox" replace />} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/review/:submissionId" element={<Review />} />
        <Route path="/student/:studentId" element={<StudentProfile />} />
        <Route path="/dashboard/:classId" element={<Dashboard />} />
      </Routes>
    </>
  );
}
