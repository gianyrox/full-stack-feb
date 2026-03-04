import { createBrowserRouter } from "react-router-dom";
import { Layout } from "./components/Layout";
import { PolicyListPage } from "./pages/PolicyListPage";
import { PolicyDetailPage } from "./pages/PolicyDetailPage";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <PolicyListPage /> },
      { path: "/policy/:id", element: <PolicyDetailPage /> },
    ],
  },
]);
