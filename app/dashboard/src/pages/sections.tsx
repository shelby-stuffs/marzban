import { Box, Button, Heading, VStack } from "@chakra-ui/react";
import { Header } from "components/Header";
import { Statistics } from "components/Statistics";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

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
  useReturnHomeOnClose((s) => s.isEditingHosts);
  useEffect(() => {
    useDashboard.getState().onEditingHosts(true);
    return () => {
      useDashboard.getState().onEditingHosts(false);
    };
  }, []);
  return null;
};

export const NodesRoute: FC = () => {
  useReturnHomeOnClose((s) => s.isEditingNodes);
  useEffect(() => {
    useDashboard.getState().onEditingNodes(true);
    return () => {
      useDashboard.getState().onEditingNodes(false);
    };
  }, []);
  return null;
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
      <Header />
      <Statistics />
      <Box>
        <Heading size="sm" mb="2">
          {t("core.title", "Core settings")}
        </Heading>
        <Button
          colorScheme="primary"
          onClick={() => useDashboard.setState({ isEditingCore: true })}
        >
          {t("header.coreSettings", "Core settings")}
        </Button>
      </Box>
    </VStack>
  );
};
