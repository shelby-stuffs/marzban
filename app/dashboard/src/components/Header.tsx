import {
  Box,
  chakra,
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
  Bars3Icon,
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
import GitHubButton from "react-github-btn";
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
const MenuIcon = chakra(Bars3Icon, iconProps);
const LogoutIcon = chakra(ArrowLeftOnRectangleIcon, iconProps);
const DonationIcon = chakra(CurrencyDollarIcon, iconProps);
const ResetUsageIcon = chakra(DocumentMinusIcon, iconProps);
const NotificationCircle = chakra(Box, {
  baseStyle: {
    bg: "yellow.500",
    w: "2",
    h: "2",
    rounded: "full",
    position: "absolute",
  },
});

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
  const gBtnColor = colorMode === "dark" ? "dark_dimmed" : colorMode;

  const handleOnClose = () => {
    localStorage.setItem(NOTIFICATION_KEY, new Date().getTime().toString());
    setShowDonationNotif(false);
  };

  return (
    <HStack gap={2} justifyContent="space-between" position="relative" mb="4">
      <Text as="h1" fontWeight="semibold" fontSize="2xl">
        {title ?? t("users")}
      </Text>
      <HStack alignItems="center">
        {actions}
        <Menu>
          <MenuButton
            as={IconButton}
            size="sm"
            variant="outline"
            aria-label="menu"
          >
            <MenuIcon />
          </MenuButton>
          <MenuList minW="180px" zIndex={99999}>
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
            <Link to="/login">
              <MenuItem fontSize="sm" icon={<LogoutIcon />}>
                {t("header.logout")}
              </MenuItem>
            </Link>
          </MenuList>
        </Menu>
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
        <Box display="flex" alignItems="center" pr="2">
          <GitHubButton
            href={REPO_URL}
            data-color-scheme={`no-preference: ${gBtnColor}; light: ${gBtnColor}; dark: ${gBtnColor};`}
            data-size="large"
            data-show-count="true"
            aria-label="Star Marzban on GitHub"
          >
            Star
          </GitHubButton>
        </Box>
      </HStack>
    </HStack>
  );
};
