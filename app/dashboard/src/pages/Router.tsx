import { createHashRouter } from "react-router-dom";
import { fetch } from "../service/http";
import { getAuthToken } from "../utils/authStorage";
import { Dashboard } from "./Dashboard";
import { Layout } from "./Layout";
import { Login } from "./Login";
import { CoreRoute, HostsRoute, NodesRoute, NodesUsageRoute } from "./sections";

const fetchAdminLoader = () => {
  return fetch("/admin", {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });
};

export const router = createHashRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <Login />,
    loader: fetchAdminLoader,
    children: [
      { index: true, element: <Dashboard /> },
      {
        path: "hosts",
        element: (
          <>
            <Dashboard />
            <HostsRoute />
          </>
        ),
      },
      {
        path: "nodes",
        element: (
          <>
            <Dashboard />
            <NodesRoute />
          </>
        ),
      },
      {
        path: "nodes-usage",
        element: (
          <>
            <Dashboard />
            <NodesUsageRoute />
          </>
        ),
      },
      { path: "core", element: <CoreRoute /> },
    ],
  },
  {
    path: "/login/",
    element: <Login />,
  },
]);
