import { BrowserRouter } from "react-router";
import { AppRoutes } from "./routes";
import { DemoSessionContext, useSessionState } from "./useDemoSession";
import { RuntimeContext, useRuntimeState } from "./runtime";
import { SessionGate } from "./SessionGate";
export default function App() {
  const runtime = useRuntimeState();
  return (
    <RuntimeContext value={runtime}>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <SessionGate>
          <Session key={`${runtime.mode}:${runtime.epoch}`} />
        </SessionGate>
      </BrowserRouter>
    </RuntimeContext>
  );
}
function Session() {
  const session = useSessionState();
  return (
    <DemoSessionContext value={session}>
      <AppRoutes />
    </DemoSessionContext>
  );
}
