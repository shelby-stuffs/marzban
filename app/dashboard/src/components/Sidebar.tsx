import { chakra, Flex, Text, VStack } from "@chakra-ui/react";
import {
  CloudIcon,
  Cog6ToothIcon,
  LinkIcon,
  ShieldCheckIcon,
  SquaresPlusIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import useGetUser from "hooks/useGetUser";
import { FC } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

const navIconStyle = { baseStyle: { w: 5, h: 5 } };
const UsersNavIcon = chakra(UsersIcon, navIconStyle);
const HostsNavIcon = chakra(LinkIcon, navIconStyle);
const NodesNavIcon = chakra(SquaresPlusIcon, navIconStyle);
const CoreNavIcon = chakra(Cog6ToothIcon, navIconStyle);
const WireGuardNavIcon = chakra(ShieldCheckIcon, navIconStyle);
const XHTTPNavIcon = chakra(CloudIcon, navIconStyle);
const darkBorder = { borderColor: "gray.700" };
const hoverStyle = { bg: "gray.100", _dark: { bg: "gray.700" } };
const railDisplay = { base: "none", md: "flex" };

type NavItemProps = { to: string; end?: boolean; icon: any; label: string; onClick?: () => void };
const NavItem: FC<NavItemProps> = ({ to, end, icon: IconEl, label, onClick }) => (
  <NavLink to={to} end={end} onClick={onClick}>
    {(navData) => (
      <Flex align="center" gap="3" px="3" py="2" borderRadius="8px" fontSize="sm" fontWeight="medium" cursor="pointer"
        bg={navData.isActive ? "primary.500" : "transparent"} color={navData.isActive ? "white" : "inherit"}
        _hover={navData.isActive ? undefined : hoverStyle}>
        <IconEl /><Text>{label}</Text>
      </Flex>
    )}
  </NavLink>
);

export const SidebarContent: FC<{ onNavigate?: () => void }> = ({ onNavigate }) => {
  const { t } = useTranslation();
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();
  const isSudo = !getUserIsPending && getUserIsSuccess ? userData?.is_sudo : false;
  return (
    <VStack align="stretch" spacing="1" p="3" w="full">
      <Flex align="center" gap="2" px="2" py="3" mb="2"><Text fontWeight="bold" fontSize="lg">Marzban</Text></Flex>
      <NavItem to="/" end icon={UsersNavIcon} label={t("users", "Users")} onClick={onNavigate} />
      {isSudo && <NavItem to="/hosts" icon={HostsNavIcon} label={t("hosts", "Hosts")} onClick={onNavigate} />}
      {isSudo && <NavItem to="/xhttp" icon={XHTTPNavIcon} label={t("xhttp.title", "XHTTP")} onClick={onNavigate} />}
      {isSudo && <NavItem to="/nodes" icon={NodesNavIcon} label={t("nodes", "Nodes")} onClick={onNavigate} />}
      {isSudo && <NavItem to="/core" icon={CoreNavIcon} label={t("core.title", "Core")} onClick={onNavigate} />}
      {isSudo && <NavItem to="/wireguard" icon={WireGuardNavIcon} label={t("wireguard.title", "WireGuard")} onClick={onNavigate} />}
    </VStack>
  );
};

export const Sidebar: FC = () => (
  <Flex as="aside" direction="column" display={railDisplay} w="60" flexShrink={0} borderRight="1px solid"
    borderColor="light-border" _dark={darkBorder} position="sticky" top="0" h="100vh" overflowY="auto">
    <SidebarContent />
  </Flex>
);

export default Sidebar;
