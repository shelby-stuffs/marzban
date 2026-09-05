import { Box, BoxProps, chakra, Flex, HStack, Text } from "@chakra-ui/react";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  ChartBarIcon,
  ChartPieIcon,
  CpuChipIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import { useDashboard } from "contexts/DashboardContext";
import { FC, PropsWithChildren, ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { formatBytes, numberWithCommas } from "utils/formatByte";

const iconStyle = { baseStyle: { w: 4, h: 4 } };
const TotalUsersIcon = chakra(UsersIcon, iconStyle);
const NetworkIcon = chakra(ChartBarIcon, iconStyle);
const MemoryIcon = chakra(ChartPieIcon, iconStyle);
const CpuIcon = chakra(CpuChipIcon, iconStyle);
const DownloadIcon = chakra(ArrowDownIcon, iconStyle);
const UploadIcon = chakra(ArrowUpIcon, iconStyle);

type StatisticCardProps = {
  title: string;
  content: ReactNode;
  icon: ReactElement;
};

const StatisticCard: FC<PropsWithChildren<StatisticCardProps>> = ({
  title,
  content,
  icon,
}) => {
  return (
    <Box
      position="relative"
      px="4"
      py="3.5"
      borderWidth="1px"
      borderColor="terminal.border"
      bg="terminal.surface"
      borderRadius="6px"
      boxShadow="panel"
      overflow="hidden"
      transition="border-color .12s ease-out"
      _hover={{ borderColor: "primary.700" }}
    >
      <Box
        position="absolute"
        left="0"
        top="0"
        bottom="0"
        w="2px"
        bg="primary.500"
        opacity="0.6"
      />
      <HStack align="center" spacing="2" color="gray.400" mb="2">
        <Flex color="primary.400">{icon}</Flex>
        <Text
          fontFamily="mono"
          fontSize="10px"
          fontWeight="500"
          textTransform="uppercase"
          letterSpacing="0.14em"
          noOfLines={1}
        >
          {title}
        </Text>
      </HStack>
      <Box
        fontFamily="mono"
        fontSize="2xl"
        fontWeight="600"
        letterSpacing="-0.01em"
        color="terminal.text"
      >
        {content}
      </Box>
    </Box>
  );
};

const Unit: FC<PropsWithChildren> = ({ children }) => (
  <Text
    as="span"
    fontFamily="mono"
    fontWeight="400"
    fontSize="sm"
    color="gray.500"
    display="inline-block"
    pb="3px"
  >
    {children}
  </Text>
);

export const StatisticsQueryKey = "statistics-query-key";
export const Statistics: FC<BoxProps> = (props) => {
  const { version } = useDashboard();
  const { data: systemData } = useQuery({
    queryKey: StatisticsQueryKey,
    queryFn: () => fetch("/system"),
    refetchInterval: 5000,
    onSuccess: ({ version: currentVersion }) => {
      if (version !== currentVersion)
        useDashboard.setState({ version: currentVersion });
    },
  });
  const { t } = useTranslation();
  return (
    <Box
      display="grid"
      gridTemplateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }}
      gap={3}
      {...props}
    >
      <StatisticCard
        title={t("activeUsers")}
        content={
          systemData && (
            <HStack alignItems="flex-end" spacing="1.5">
              <Text>{numberWithCommas(systemData.users_active)}</Text>
              <Unit>/ {numberWithCommas(systemData.total_user)}</Unit>
            </HStack>
          )
        }
        icon={<TotalUsersIcon />}
      />
      <StatisticCard
        title={t("dataUsage")}
        content={
          systemData &&
          formatBytes(
            systemData.incoming_bandwidth + systemData.outgoing_bandwidth
          )
        }
        icon={<NetworkIcon />}
      />
      <StatisticCard
        title={t("memoryUsage")}
        content={
          systemData && (
            <HStack alignItems="flex-end" spacing="1.5">
              <Text>{formatBytes(systemData.mem_used, 1, true)[0]}</Text>
              <Unit>
                {formatBytes(systemData.mem_used, 1, true)[1]} /{" "}
                {formatBytes(systemData.mem_total, 1)}
              </Unit>
            </HStack>
          )
        }
        icon={<MemoryIcon />}
      />
      <StatisticCard
        title={t("cpuUsage")}
        content={
          systemData && (
            <HStack alignItems="flex-end" spacing="1.5">
              <Text>{systemData.cpu_usage.toFixed(1)}%</Text>
              <Unit>{systemData.cpu_cores} cores</Unit>
            </HStack>
          )
        }
        icon={<CpuIcon />}
      />
      <StatisticCard
        title={t("downloadSpeed")}
        content={
          systemData && (
            <HStack alignItems="flex-end" spacing="1.5">
              <Text>
                {(
                  (systemData.incoming_bandwidth_speed * 8) /
                  1_000_000
                ).toFixed(1)}
              </Text>
              <Unit>Mbit/s</Unit>
            </HStack>
          )
        }
        icon={<DownloadIcon />}
      />
      <StatisticCard
        title={t("uploadSpeed")}
        content={
          systemData && (
            <HStack alignItems="flex-end" spacing="1.5">
              <Text>
                {(
                  (systemData.outgoing_bandwidth_speed * 8) /
                  1_000_000
                ).toFixed(1)}
              </Text>
              <Unit>Mbit/s</Unit>
            </HStack>
          )
        }
        icon={<UploadIcon />}
      />
    </Box>
  );
};
