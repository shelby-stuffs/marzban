import { Box, chakra, Flex, HStack, Text, VStack } from "@chakra-ui/react";
import {
  ChartPieIcon,
  Cog6ToothIcon,
  LinkIcon,
  SquaresPlusIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import useGetUser from "hooks/useGetUser";
import { FC } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

const iconProps = { baseStyle: { w: 5, h: 5 } };
const UsersNav = chakra(UsersIcon, iconProps);
const HostsNav = chakra(LinkIcon, iconProps);
const NodesNav = chakra(SquaresPlusIcon, iconProps);
const UsageNav = chakra(ChartPieIcon, iconProps);
const CoreNav = chakra(Cog6ToothIcon, iconProps);

type Item = {
  to: string;
  label: string;
  icon: any;
  sudo?: boolean;
};

const darkBorder = { borderColor: "gray.600" };
const hoverStyle = { bg: "blackAlpha.100", textDecoration: "none" };
const activeStyle = { bg: "primary.500", color: "white" };

export const Sidebar: FC = () => {
  const { t } = useTranslation();
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();
  const isSudo =
    !getUserIsPending && getUserIsSuccess && Boolean(userData?.is_sudo);

  const items: Item[] = [
    { to: "/", label: t("users", "Users"), icon: UsersNav },
    {
      to: "/hosts",
      label: t("header.hostSettings", "Hosts"),
      icon: HostsNav,
      sudo: true,
    },
    {
      to: "/nodes",
      label: t("header.nodeSettings", "Nodes"),
      icon: NodesNav,
      sudo: true,
    },
    {
      to: "/nodes-usage",
      label: t("header.nodesUsage", "Nodes usage"),
      icon: UsageNav,
      sudo: true,
    },
    {
      to: "/core",
      label: t("header.coreSettings", "Core"),
      icon: CoreNav,
      sudo: true,
    },
  ];

  return (
    <Flex
      direction="column"
      w="60"
      flexShrink={0}
      borderRightWidth="1px"
      borderColor="light-border"
      _dark={darkBorder}
      p="3"
      position="sticky"
      top="0"
      h="100vh"
    >
      <HStack px="2" py="3" spacing="2">
        <Box boxSize="7" borderRadius="8px" bg="primary.500" />
        <Text fontWeight="bold" fontSize="lg">
          Marzban
        </Text>
      </HStack>
      <VStack align="stretch" spacing="1" mt="2">
        {items.map((item) => {
          if (item.sudo && !isSudo) return null;
          const Icon = item.icon;
          return (
            <NavLink to={item.to} end={item.to === "/"} key={item.to}>
              {(nav) => (
                <HStack
                  spacing="3"
                  px="3"
                  py="2"
                  borderRadius="8px"
                  fontSize="sm"
                  fontWeight="medium"
                  bg={nav.isActive ? "primary.500" : "transparent"}
                  color={nav.isActive ? "white" : "inherit"}
                  _hover={nav.isActive ? activeStyle : hoverStyle}
                >
                  <Icon />
                  <Text>{item.label}</Text>
                </HStack>
              )}
            </NavLink>
          );
        })}
      </VStack>
    </Flex>
  );
};

export default Sidebar;
