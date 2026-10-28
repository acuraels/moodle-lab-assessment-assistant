import { BrowserRouter } from "react-router";
import { AppRoutes } from "./routes";
import { DemoSessionContext, useSessionState } from "./useDemoSession";
export default function App() {
  const session = useSessionState();
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <DemoSessionContext value={session}>
        <AppRoutes />
      </DemoSessionContext>
    </BrowserRouter>
  );
}
