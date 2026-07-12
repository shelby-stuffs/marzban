import { Box, VStack } from "@chakra-ui/react";
import { CoreSettingsPanel } from "components/CoreSettingsModal";
import { Header } from "components/Header";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { Statistics } from "components/Statistics";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

const darkBorder = { borderColor: "gray.600" };

const useReturnHomeOnClose = (
  selector: (s: ReturnType<typeof useDashboard.getState>) => boolean
) => {
  const navigate = useNavigate();
  useEffect(() => {
    const unsub = useDashboard.subscribe(selector, (open) => {
      if (!open) navigate("/");
    });
    return () => {
      unsub();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
};

export const HostsRoute: FC = () => {
  const { t } = useTranslation();
  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("header.hostSettings", "Hosts")} />
      <Box
        borderWidth="1px"
        borderColor="light-border"
        _dark={darkBorder}
        borderRadius="10px"
        p="4"
      >
        <HostsDialog />
      </Box>
    </VStack>
  );
};

export const NodesRoute: FC = () => {
  const { t } = useTranslation();
  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("header.nodeSettings", "Nodes")} />
      <Box
        borderWidth="1px"
        borderColor="light-border"
        _dark={darkBorder}
        borderRadius="10px"
        p="4"
      >
        <NodesDialog />
      </Box>
    </VStack>
  );
};

export const NodesUsageRoute: FC = () => {
  useReturnHomeOnClose((s) => s.isShowingNodesUsage);
  useEffect(() => {
    useDashboard.getState().onShowingNodesUsage(true);
    return () => {
      useDashboard.getState().onShowingNodesUsage(false);
    };
  }, []);
  return null;
};

export const CoreRoute: FC = () => {
  const { t } = useTranslation();
  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("core.title", "Core")} />
      <Statistics />
      <Box
        borderWidth="1px"
        borderColor="light-border"
        _dark={darkBorder}
        borderRadius="10px"
        p="4"
      >
        <CoreSettingsPanel />
      </Box>
    </VStack>
  );
};
