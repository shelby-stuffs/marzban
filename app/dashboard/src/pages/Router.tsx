import { Navigate, createHashRouter } from "react-router-dom";
import { fetch } from "../service/http";
import { getAuthToken } from "../utils/authStorage";
import { Dashboard } from "./Dashboard";
import { Layout } from "./Layout";
import { Login } from "./Login";
import { CoreRoute, HostsRoute, NodesRoute } from "./sections";
import { SingBoxSettingsPage } from "./SingBoxSettings";
import { SubscriptionSettingsPage } from "./SubscriptionSettings";
import { WireGuardOutbounds } from "./WireGuardOutbounds";
import { XHTTPSettingsPage } from "./XHTTPSettings";

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
      { path: "hosts", element: <HostsRoute /> },
      { path: "nodes", element: <NodesRoute /> },
      { path: "core", element: <CoreRoute /> },
      { path: "wireguard", element: <WireGuardOutbounds /> },
      { path: "xhttp", element: <XHTTPSettingsPage /> },
      { path: "singbox", element: <SingBoxSettingsPage /> },
      { path: "hysteria2", element: <Navigate to="/singbox" replace /> },
      { path: "subscriptions", element: <SubscriptionSettingsPage /> },
    ],
  },
  { path: "/login/", element: <Login /> },
]);
