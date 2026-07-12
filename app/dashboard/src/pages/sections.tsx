import { Box, VStack } from "@chakra-ui/react";
import { CoreSettingsPanel } from "components/CoreSettingsModal";
import { Header } from "components/Header";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { NodesUsage } from "components/NodesUsage";
import { Statistics } from "components/Statistics";
import { FC } from "react";
import { useTranslation } from "react-i18next";

const darkBorder = { borderColor: "gray.600" };

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
      <Box
        borderWidth="1px"
        borderColor="light-border"
        _dark={darkBorder}
        borderRadius="10px"
        p="4"
      >
        <NodesUsage />
      </Box>
    </VStack>
  );
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
