import {
  Box,
  chakra,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerOverlay,
  Flex,
  IconButton,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import { Bars3Icon } from "@heroicons/react/24/outline";
import { DeleteUserModal } from "components/DeleteUserModal";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { NodesUsage } from "components/NodesUsage";
import { QRCodeDialog } from "components/QRCodeDialog";
import { ResetAllUsageModal } from "components/ResetAllUsageModal";
import { ResetUserUsageModal } from "components/ResetUserUsageModal";
import { RevokeSubscriptionModal } from "components/RevokeSubscriptionModal";
import { Sidebar, SidebarContent } from "components/Sidebar";
import { UserDialog } from "components/UserDialog";
import { FC } from "react";
import { Outlet } from "react-router-dom";

const MenuIcon = chakra(Bars3Icon, { baseStyle: { w: 5, h: 5 } });
const contentPad = { base: 4, md: 6 };
const topbarDisplay = { base: "flex", md: "none" };
const darkPanel = { bg: "gray.800", borderColor: "gray.700" };

export const Layout: FC = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  return (
    <Flex direction="column" minH="100vh">
      <Flex
        as="header"
        display={topbarDisplay}
        align="center"
        gap="3"
        px="4"
        py="3"
        borderBottom="1px solid"
        borderColor="light-border"
        _dark={darkPanel}
        position="sticky"
        top="0"
        zIndex={20}
        bg="white"
      >
        <IconButton
          aria-label="open menu"
          variant="outline"
          size="sm"
          onClick={onOpen}
        >
          <MenuIcon />
        </IconButton>
        <Text fontWeight="bold" fontSize="lg">
          Marzban
        </Text>
      </Flex>
      <Flex flex="1" align="stretch">
        <Sidebar />
        <Box flex="1" minW="0" p={contentPad}>
          <Outlet />
        </Box>
      </Flex>
      <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent maxW="260px">
          <DrawerBody p="0">
            <SidebarContent onNavigate={onClose} />
          </DrawerBody>
        </DrawerContent>
      </Drawer>
      <UserDialog />
      <DeleteUserModal />
      <QRCodeDialog />
      <HostsDialog />
      <ResetUserUsageModal />
      <RevokeSubscriptionModal />
      <NodesDialog />
      <NodesUsage />
      <ResetAllUsageModal />
    </Flex>
  );
};

export default Layout;
