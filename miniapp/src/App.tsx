import { Navigate, Route, Routes } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { Inbox } from "./pages/Inbox";
import { Review } from "./pages/Review";
import { StudentProfile } from "./pages/StudentProfile";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/inbox" replace />} />
      <Route path="/inbox" element={<Inbox />} />
      <Route path="/review/:submissionId" element={<Review />} />
      <Route path="/student/:studentId" element={<StudentProfile />} />
      <Route path="/dashboard/:classId" element={<Dashboard />} />
    </Routes>
  );
}
