import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AppBar } from "./components/AppBar";
import { BottomNav } from "./components/BottomNav";
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
import { HomeworkCreate } from "./pages/homework/HomeworkCreate";
import { HomeworkEdit } from "./pages/homework/HomeworkEdit";
import { HomeworkList } from "./pages/homework/HomeworkList";
import { HomeworkView } from "./pages/homework/HomeworkView";
import { RoadmapCreate } from "./pages/roadmap/RoadmapCreate";
import { RoadmapEdit } from "./pages/roadmap/RoadmapEdit";
import { RoadmapList } from "./pages/roadmap/RoadmapList";
import { RoadmapView } from "./pages/roadmap/RoadmapView";

function StartParamRouter() {
  const navigate = useNavigate();

  useEffect(() => {
    const param = maxBridge.getStartParam();
    if (!param) return;
    const [kind, ...rest] = param.split("_");
    const id = rest.join("_");
    if (kind === "submission" && id) navigate(`/review/${id}`, { replace: true });
    else if (kind === "student" && id) navigate(`/student/${id}`, { replace: true });
    else if (kind === "class" && id) navigate(`/dashboard/${id}`, { replace: true });
    else if (kind === "roadmap" && id) navigate(`/roadmaps/${id}`, { replace: true });
    else if (kind === "homework" && id) navigate(`/homework/${id}`, { replace: true });
    else if (kind === "tab" && id === "roadmap") navigate("/roadmaps", { replace: true });
    else if (kind === "tab" && id === "homework") navigate("/homework", { replace: true });
    else if (kind === "tab" && id === "check") navigate("/", { replace: true });
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

        <Route path="/roadmaps" element={<RoadmapList />} />
        <Route path="/roadmaps/new" element={<RoadmapCreate />} />
        <Route path="/roadmaps/:roadmapId" element={<RoadmapView />} />
        <Route path="/roadmaps/:roadmapId/edit" element={<RoadmapEdit />} />

        <Route path="/homework" element={<HomeworkList />} />
        <Route path="/homework/new" element={<HomeworkCreate />} />
        <Route path="/homework/:homeworkId" element={<HomeworkView />} />
        <Route path="/homework/:homeworkId/edit" element={<HomeworkEdit />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
    </>
  );
}
