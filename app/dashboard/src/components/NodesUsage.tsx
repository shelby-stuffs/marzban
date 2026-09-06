import {
  Box,
  CircularProgress,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Text,
  VStack,
  chakra,
  useColorMode,
} from "@chakra-ui/react";
import { ChartPieIcon } from "@heroicons/react/24/outline";
import { FilterUsageType, useDashboard } from "contexts/DashboardContext";
import { useNodes } from "contexts/NodesContext";
import dayjs from "dayjs";
import { FC, Suspense, useEffect, useState } from "react";
import ReactApexChart from "react-apexcharts";
import { useTranslation } from "react-i18next";
import { Icon } from "./Icon";
import { UsageFilter, createUsageConfig } from "./UsageFilter";

const UsageIcon = chakra(ChartPieIcon, {
  baseStyle: {
    w: 5,
    h: 5,
  },
});

export type NodesUsageProps = {};

export const NodesUsage: FC<NodesUsageProps> = () => {
  const { isShowingNodesUsage, onShowingNodesUsage } = useDashboard();
  const { fetchNodesUsage } = useNodes();
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const { colorMode } = useColorMode();

  const usageTitle = t("userDialog.total");
  const [usage, setUsage] = useState(createUsageConfig(colorMode, usageTitle));
  const [usageFilter, setUsageFilter] = useState("1m");
  const fetchUsageWithFilter = (query: FilterUsageType) => {
    fetchNodesUsage(query).then((data: any) => {
      const labels = [];
      const series = [];
      for (const key in data.usages) {
        const entry = data.usages[key];
        series.push(entry.uplink + entry.downlink);
        labels.push(entry.node_name);
      }
      setUsage(createUsageConfig(colorMode, usageTitle, series, labels));
    });
  };

  useEffect(() => {
    if (true) {
      fetchUsageWithFilter({
        start: dayjs().utc().subtract(30, "day").format("YYYY-MM-DDTHH:00:00"),
      });
    }
  }, []);

  const onClose = () => {
    onShowingNodesUsage(false);
    setUsageFilter("1m");
  };

  const disabled = loading;

  return (
    <Box w="full">
      <Box w="full">
        <Box pt={2} mb={2}>
          <HStack gap={2}>
            <Icon color="primary">
              <UsageIcon color="white" />
            </Icon>
            <Text fontWeight="semibold" fontSize="lg">
              {t("header.nodesUsage")}
            </Text>
          </HStack>
        </Box>
        <Box>
          <VStack gap={4}>
            <UsageFilter
              defaultValue={usageFilter}
              onChange={(filter, query) => {
                setUsageFilter(filter);
                fetchUsageWithFilter(query);
              }}
            />
            <Box justifySelf="center" w="full" maxW="420px" mt="2" minH="280px">
              <Suspense fallback={<CircularProgress isIndeterminate />}>
                <ReactApexChart
                  options={usage.options}
                  series={usage.series}
                  type="donut"
                  width="100%"
                  height={320}
                />
              </Suspense>
            </Box>
          </VStack>
        </Box>
      </Box>
    </Box>
  );
};
