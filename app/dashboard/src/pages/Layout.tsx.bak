import { Box, Flex } from "@chakra-ui/react";
import { CoreSettingsModal } from "components/CoreSettingsModal";
import { DeleteUserModal } from "components/DeleteUserModal";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { NodesUsage } from "components/NodesUsage";
import { QRCodeDialog } from "components/QRCodeDialog";
import { ResetAllUsageModal } from "components/ResetAllUsageModal";
import { ResetUserUsageModal } from "components/ResetUserUsageModal";
import { RevokeSubscriptionModal } from "components/RevokeSubscriptionModal";
import { Sidebar } from "components/Sidebar";
import { UserDialog } from "components/UserDialog";
import { FC } from "react";
import { Outlet } from "react-router-dom";

export const Layout: FC = () => {
  return (
    <Flex minH="100vh" align="stretch">
      <Sidebar />
      <Box flex="1" minW="0" p="6">
        <Outlet />
      </Box>
      <UserDialog />
      <DeleteUserModal />
      <QRCodeDialog />
      <HostsDialog />
      <ResetUserUsageModal />
      <RevokeSubscriptionModal />
      <NodesDialog />
      <NodesUsage />
      <ResetAllUsageModal />
      <CoreSettingsModal />
    </Flex>
  );
};

export default Layout;
