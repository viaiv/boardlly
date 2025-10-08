import { AppRoutes } from "@/routes/AppRoutes";
import { Toaster } from "@/components/ui/sonner";

export function App() {
  return (
    <>
      <AppRoutes />
      <Toaster />
    </>
  );
}

export default App;
