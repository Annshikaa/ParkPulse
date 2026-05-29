import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";
import { router } from "./router";

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "hsl(222, 47%, 14%)",
            border: "1px solid hsl(216, 34%, 20%)",
            color: "hsl(213, 31%, 91%)",
          },
        }}
      />
    </>
  );
}
