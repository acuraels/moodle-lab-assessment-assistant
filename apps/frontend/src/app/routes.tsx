import { Navigate, Route, Routes } from "react-router";
import { AppLayout } from "./AppLayout";
import { NotFound } from "./NotFound";
import { TeacherDashboard } from "../features/teacher/TeacherDashboard";
import { SettingsPanel } from "../features/teacher/SettingsPanel";
import { SubmissionRoute } from "../features/teacher/SubmissionRoute";
import { StudentWorkspace } from "../features/student/StudentWorkspace";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/teacher" replace />} />
        <Route path="teacher">
          <Route element={<TeacherDashboard />}>
            <Route index element={null} />
            <Route path="submissions/:id" element={<SubmissionRoute />} />
          </Route>
          <Route path="settings" element={<SettingsPanel />} />
        </Route>
        <Route path="student">
          <Route index element={<Navigate to="/student/check" replace />} />
          <Route path="check" element={<StudentWorkspace />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
