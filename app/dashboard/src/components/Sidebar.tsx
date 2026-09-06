import { Box, chakra, Flex, HStack, Text, VStack } from "@chakra-ui/react";
import {
  BoltIcon,
  CloudIcon,
  Cog6ToothIcon,
  LinkIcon,
  QueueListIcon,
  ShieldCheckIcon,
  SquaresPlusIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import useGetUser from "hooks/useGetUser";
import { FC } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

const navIconStyle = { baseStyle: { w: "4", h: "4" } };
const UsersNavIcon = chakra(UsersIcon, navIconStyle);
const HostsNavIcon = chakra(LinkIcon, navIconStyle);
const NodesNavIcon = chakra(SquaresPlusIcon, navIconStyle);
const CoreNavIcon = chakra(Cog6ToothIcon, navIconStyle);
const WireGuardNavIcon = chakra(ShieldCheckIcon, navIconStyle);
const XHTTPNavIcon = chakra(CloudIcon, navIconStyle);
const SingBoxNavIcon = chakra(BoltIcon, navIconStyle);
const SubscriptionsNavIcon = chakra(QueueListIcon, navIconStyle);

const railDisplay = { base: "none", md: "flex" };
const hoverStyle = { bg: "terminal.overlay", color: "primary.300" };

type NavItemProps = {
  to: string;
  end?: boolean;
  icon: any;
  label: string;
  onClick?: () => void;
};

const NavItem: FC<NavItemProps> = ({ to, end, icon: IconEl, label, onClick }) => (
  <NavLink to={to} end={end} onClick={onClick}>
    {(navData) => (
      <Flex
        align="center"
        gap="2.5"
        px="3"
        py="2"
        position="relative"
        borderRadius="3px"
        fontFamily="mono"
        fontSize="sm"
        letterSpacing="0.01em"
        cursor="pointer"
        transition="background .12s ease-out, color .12s ease-out"
        bg={navData.isActive ? "rgba(0, 224, 140, 0.08)" : "transparent"}
        color={navData.isActive ? "primary.300" : "gray.400"}
        _hover={navData.isActive ? undefined : hoverStyle}
      >
        <Box
          position="absolute"
          left="0"
          top="1.5"
          bottom="1.5"
          w="2px"
          borderRadius="1px"
          bg={navData.isActive ? "primary.500" : "transparent"}
        />
        <IconEl />
        <Text>{label}</Text>
      </Flex>
    )}
  </NavLink>
);

const SectionLabel: FC<{ children: string }> = ({ children }) => (
  <Text
    px="3"
    pt="4"
    pb="1"
    fontFamily="mono"
    fontSize="10px"
    fontWeight="500"
    textTransform="uppercase"
    letterSpacing="0.14em"
    color="gray.500"
  >
    {children}
  </Text>
);

export const SidebarContent: FC<{ onNavigate?: () => void }> = ({ onNavigate }) => {
  const { t } = useTranslation();
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();
  const isSudo = !getUserIsPending && getUserIsSuccess ? userData?.is_sudo : false;

  return (
    <VStack align="stretch" spacing="0.5" p="3" w="full">
      <HStack spacing="2" px="3" py="3" mb="1" align="center">
        <Box boxSize="2" borderRadius="1px" bg="primary.500" boxShadow="glow" />
        <Text fontFamily="mono" fontWeight="600" fontSize="md" letterSpacing="0.04em">
          marzban
        </Text>
      </HStack>

      <NavItem to="/" end icon={UsersNavIcon} label={t("users", "Users")} onClick={onNavigate} />

      {isSudo && (
        <>
          <SectionLabel>delivery</SectionLabel>
          <NavItem
            to="/subscriptions"
            icon={SubscriptionsNavIcon}
            label={t("subscription.title", "Subscriptions")}
            onClick={onNavigate}
          />

          <SectionLabel>transport</SectionLabel>
          <NavItem to="/hosts" icon={HostsNavIcon} label={t("hosts", "Hosts")} onClick={onNavigate} />
          <NavItem to="/xhttp" icon={XHTTPNavIcon} label={t("xhttp.title", "XHTTP")} onClick={onNavigate} />
          <NavItem to="/singbox" icon={SingBoxNavIcon} label={t("singbox.title", "sing-box")} onClick={onNavigate} />
          <NavItem
            to="/wireguard"
            icon={WireGuardNavIcon}
            label={t("wireguard.title", "WireGuard")}
            onClick={onNavigate}
          />

          <SectionLabel>infrastructure</SectionLabel>
          <NavItem to="/nodes" icon={NodesNavIcon} label={t("nodes", "Nodes")} onClick={onNavigate} />
          <NavItem to="/core" icon={CoreNavIcon} label={t("core.title", "Core")} onClick={onNavigate} />
        </>
      )}
    </VStack>
  );
};

export const Sidebar: FC = () => (
  <Flex
    as="aside"
    direction="column"
    display={railDisplay}
    w="56"
    flexShrink={0}
    borderRight="1px solid"
    borderColor="terminal.border"
    bg="terminal.surface"
    position="sticky"
    top="0"
    h="100vh"
    overflowY="auto"
  >
    <SidebarContent />
  </Flex>
);

export default Sidebar;
