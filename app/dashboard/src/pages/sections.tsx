import { VStack } from "@chakra-ui/react";
import { CoreSettingsPanel } from "components/CoreSettingsModal";
import { Header } from "components/Header";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { NodesUsage } from "components/NodesUsage";
import { Panel } from "components/Panel";
import { Statistics } from "components/Statistics";
import { FC } from "react";
import { useTranslation } from "react-i18next";

export const HostsRoute: FC = () => {
  const { t } = useTranslation();
  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("header.hostSettings", "Hosts")} />
      <Panel label="proxy hosts">
        <HostsDialog />
      </Panel>
    </VStack>
  );
};

export const NodesRoute: FC = () => {
  const { t } = useTranslation();
  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("header.nodeSettings", "Nodes")} />
      <Panel label="nodes">
        <NodesDialog />
      </Panel>
      <Panel label="traffic per node">
        <NodesUsage />
      </Panel>
    </VStack>
  );
};

export const CoreRoute: FC = () => {
  const { t } = useTranslation();
  return (
    <VStack align="stretch" spacing="4" w="full">
      <Header title={t("core.title", "Core")} />
      <Statistics />
      <Panel label="xray core">
        <CoreSettingsPanel />
      </Panel>
    </VStack>
  );
};
