import {
  Box,
  chakra,
  Flex,
  HStack,
  IconButton,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
  useColorMode,
} from "@chakra-ui/react";
import {
  ArrowLeftOnRectangleIcon,
  ArrowTopRightOnSquareIcon,
  CurrencyDollarIcon,
  DocumentMinusIcon,
  MoonIcon,
  SunIcon,
} from "@heroicons/react/24/outline";
import { DONATION_URL, REPO_URL } from "constants/Project";
import { useDashboard } from "contexts/DashboardContext";
import differenceInDays from "date-fns/differenceInDays";
import isValid from "date-fns/isValid";
import useGetUser from "hooks/useGetUser";
import { FC, ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { updateThemeColor } from "utils/themeColor";
import { Language } from "./Language";

type HeaderProps = {
  title?: string;
  actions?: ReactNode;
};

const iconProps = {
  baseStyle: { w: 4, h: 4 },
};
const DarkIcon = chakra(MoonIcon, iconProps);
const LightIcon = chakra(SunIcon, iconProps);
const MoreIcon: FC = () => (
  <HStack spacing="0.5" h="4" align="center" justify="center">
    <Box w="3px" h="3px" bg="currentColor" />
    <Box w="3px" h="3px" bg="currentColor" />
    <Box w="3px" h="3px" bg="currentColor" />
  </HStack>
);
const LogoutIcon = chakra(ArrowLeftOnRectangleIcon, iconProps);
const DonationIcon = chakra(CurrencyDollarIcon, iconProps);
const ResetUsageIcon = chakra(DocumentMinusIcon, iconProps);
const GitHubIcon = chakra(ArrowTopRightOnSquareIcon, iconProps);
const NotificationCircle = chakra(Box, {
  baseStyle: {
    bg: "accent.500",
    w: "2",
    h: "2",
    rounded: "1px",
    position: "absolute",
  },
});

const titleSize = { base: "lg", md: "xl" };
const controlsWrap = "nowrap" as const;
const headerBorder = { borderColor: "light-border" };

const NOTIFICATION_KEY = "marzban-menu-notification";

export const shouldShowDonation = (): boolean => {
  const date = localStorage.getItem(NOTIFICATION_KEY);
  if (!date) return true;
  try {
    if (date && isValid(parseInt(date))) {
      if (differenceInDays(new Date(), new Date(parseInt(date))) >= 7)
        return true;
      return false;
    }
    return true;
  } catch (err) {
    return true;
  }
};

export const Header: FC<HeaderProps> = ({ title, actions }) => {
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();
  const isSudo = () =>
    !getUserIsPending && getUserIsSuccess ? userData.is_sudo : false;

  const { onResetAllUsage } = useDashboard();
  const { t } = useTranslation();
  const { colorMode, toggleColorMode } = useColorMode();
  const [showDonationNotif, setShowDonationNotif] = useState(
    shouldShowDonation()
  );

  const handleOnClose = () => {
    localStorage.setItem(NOTIFICATION_KEY, new Date().getTime().toString());
    setShowDonationNotif(false);
  };

  return (
    <HStack
      gap={2}
      justifyContent="space-between"
      position="relative"
      mb="5"
      pb="3"
      borderBottom="1px solid"
      borderColor="terminal.border"
      _light={headerBorder}
      flexWrap="wrap"
      w="full"
    >
      <Flex align="center" gap="2" minW="0">
        <Text
          as="span"
          fontFamily="mono"
          fontSize="sm"
          color="primary.500"
          userSelect="none"
          flexShrink={0}
        >
          &gt;
        </Text>
        <Text
          as="h1"
          fontFamily="mono"
          fontWeight="600"
          letterSpacing="0.01em"
          fontSize={titleSize}
          minW="0"
          noOfLines={1}
        >
          {title ?? t("users")}
        </Text>
      </Flex>
      <HStack
        alignItems="center"
        justifyContent="flex-end"
        gap={2}
        ml="auto"
        flexShrink={0}
        flexWrap={controlsWrap}
      >
        {actions}
        <Language />
        <IconButton
          size="sm"
          variant="outline"
          aria-label="switch theme"
          onClick={() => {
            updateThemeColor(colorMode === "dark" ? "light" : "dark");
            toggleColorMode();
          }}
        >
          {colorMode === "light" ? <DarkIcon /> : <LightIcon />}
        </IconButton>
        <Menu placement="bottom-end">
          <MenuButton
            as={IconButton}
            size="sm"
            variant="outline"
            aria-label="more actions"
          >
            <MoreIcon />
          </MenuButton>
          <MenuList minW="190px" zIndex={99999}>
            {isSudo() && (
              <MenuItem
                fontSize="sm"
                icon={<ResetUsageIcon />}
                onClick={onResetAllUsage.bind(null, true)}
              >
                {t("resetAllUsage")}
              </MenuItem>
            )}
            <Link to={DONATION_URL} target="_blank">
              <MenuItem
                fontSize="sm"
                icon={<DonationIcon />}
                position="relative"
                onClick={handleOnClose}
              >
                {t("header.donation")}
                {showDonationNotif && <NotificationCircle top="3" right="2" />}
              </MenuItem>
            </Link>
            <Link to={REPO_URL} target="_blank">
              <MenuItem fontSize="sm" icon={<GitHubIcon />}>
                GitHub
              </MenuItem>
            </Link>
            <Link to="/login">
              <MenuItem fontSize="sm" icon={<LogoutIcon />}>
                {t("header.logout")}
              </MenuItem>
            </Link>
          </MenuList>
        </Menu>
      </HStack>
    </HStack>
  );
};
