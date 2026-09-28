import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AppBar } from "./components/AppBar";
import { UserBadge } from "./components/UserBadge";
import { maxBridge } from "./max/bridge";
import { Dashboard } from "./pages/Dashboard";
import { Hub } from "./pages/Hub";
import { Review } from "./pages/Review";
import { StudentCreate } from "./pages/StudentCreate";
import { StudentPicker } from "./pages/StudentPicker";
import { StudentProfile } from "./pages/StudentProfile";
import { SubmissionFlow } from "./pages/SubmissionFlow";
import { WorkCreate } from "./pages/WorkCreate";
import { WorkPicker } from "./pages/WorkPicker";

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
      <UserBadge />
      <AppBar />
      <StartParamRouter />
      <Routes>
        <Route path="/" element={<Hub />} />
        <Route path="/submit" element={<SubmissionFlow />} />
        <Route path="/pick/work" element={<WorkPicker />} />
        <Route path="/pick/student" element={<StudentPicker />} />
        <Route path="/works/new" element={<WorkCreate />} />
        <Route path="/students/new" element={<StudentCreate />} />
        <Route path="/review/:submissionId" element={<Review />} />
        <Route path="/student/:studentId" element={<StudentProfile />} />
        <Route path="/dashboard/:classId" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
