import {
  Accordion,
  AccordionButton,
  AccordionItem,
  AccordionPanel,
  Box,
  Button,
  chakra,
  ExpandedIndex,
  HStack,
  IconButton,
  Slider,
  SliderFilledTrack,
  SliderProps,
  SliderTrack,
  Table,
  TableProps,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  useBreakpointValue,
  VStack,
} from "@chakra-ui/react";
import {
  CheckIcon,
  ChevronDownIcon,
  ClipboardIcon,
  LinkIcon,
  PencilIcon,
  QrCodeIcon,
} from "@heroicons/react/24/outline";
import { ReactComponent as AddFileIcon } from "assets/add_file.svg";
import classNames from "classnames";
import { resetStrategy, statusColors } from "constants/UserSettings";
import { useDashboard } from "contexts/DashboardContext";
import { t } from "i18next";
import { FC, Fragment, useEffect, useMemo, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";
import { User, UserUsageStat } from "types/User";
import { formatBytes } from "utils/formatByte";
import { OnlineBadge } from "./OnlineBadge";
import { OnlineStatus } from "./OnlineStatus";
import { Pagination } from "./Pagination";
import { StatusBadge } from "./StatusBadge";

const EmptySectionIcon = chakra(AddFileIcon);

const formatSpeed = (mbitps: number): string => {
  if (mbitps < 0.001) return "0 Mbit/s";
  return `${mbitps.toFixed(2)} Mbit/s`;
};

const iconProps = {
  baseStyle: {
    w: {
      base: 4,
      md: 5,
    },
    h: {
      base: 4,
      md: 5,
    },
  },
};
const CopyIcon = chakra(ClipboardIcon, iconProps);
const AccordionArrowIcon = chakra(ChevronDownIcon, iconProps);
const CopiedIcon = chakra(CheckIcon, iconProps);
const SubscriptionLinkIcon = chakra(LinkIcon, iconProps);
const QRIcon = chakra(QrCodeIcon, iconProps);
const EditIcon = chakra(PencilIcon, iconProps);
const SortIcon = chakra(ChevronDownIcon, {
  baseStyle: {
    width: "15px",
    height: "15px",
  },
});

// Row actions must stay legible on the dark canvas, so they are always ghost
// buttons with an explicit foreground instead of inheriting the solid variant.
const actionButtonStyle = {
  variant: "ghost",
  color: "gray.400",
  _hover: {
    bg: "terminal.overlay",
    color: "primary.300",
  },
  _active: {
    bg: "terminal.overlay",
    color: "primary.400",
  },
} as const;

type UsageSliderProps = {
  used: number;
  total: number | null;
  dataLimitResetStrategy: string | null;
  totalUsedTraffic: number;
} & SliderProps;

const getResetStrategy = (strategy: string): string => {
  for (var i = 0; i < resetStrategy.length; i++) {
    const entry = resetStrategy[i];
    if (entry.value == strategy) {
      return entry.title;
    }
  }
  return "No";
};
const UsageSliderCompact: FC<UsageSliderProps> = (props) => {
  const { used, total } = props;
  const isUnlimited = total === 0 || total === null;
  return (
    <HStack
      justifyContent="space-between"
      fontSize="xs"
      fontFamily="mono"
      color="gray.400"
    >
      <Text>
        {formatBytes(used)} /{" "}
        {isUnlimited ? (
          <Text as="span" fontFamily="system-ui">
            ∞
          </Text>
        ) : (
          formatBytes(total)
        )}
      </Text>
    </HStack>
  );
};
const UsageSlider: FC<UsageSliderProps> = (props) => {
  const {
    used,
    total,
    dataLimitResetStrategy,
    totalUsedTraffic,
    ...restOfProps
  } = props;
  const isUnlimited = total === 0 || total === null;
  const isReached = !isUnlimited && (used / total) * 100 >= 100;
  return (
    <>
      <Slider
        orientation="horizontal"
        value={isUnlimited ? 100 : Math.min((used / total) * 100, 100)}
        colorScheme={isReached ? "red" : "primary"}
        {...restOfProps}
      >
        <SliderTrack h="4px" borderRadius="2px" bg="terminal.overlay">
          <SliderFilledTrack borderRadius="2px" />
        </SliderTrack>
      </Slider>
      <HStack
        justifyContent="space-between"
        fontSize="xs"
        fontFamily="mono"
        color="gray.400"
      >
        <Text>
          {formatBytes(used)} /{" "}
          {isUnlimited ? (
            <Text as="span" fontFamily="system-ui">
              ∞
            </Text>
          ) : (
            formatBytes(total) +
            (dataLimitResetStrategy && dataLimitResetStrategy !== "no_reset"
              ? " " +
                t(
                  "userDialog.resetStrategy" +
                    getResetStrategy(dataLimitResetStrategy)
                )
              : "")
          )}
        </Text>
        <Text>
          {t("usersTable.total")}: {formatBytes(totalUsedTraffic)}
        </Text>
      </HStack>
    </>
  );
};
export type SortType = {
  sort: string;
  column: string;
};
export const Sort: FC<SortType> = ({ sort, column }) => {
  if (sort.includes(column))
    return (
      <SortIcon
        transform={sort.startsWith("-") ? undefined : "rotate(180deg)"}
      />
    );
  return null;
};
type UsersTableProps = {} & TableProps;
export const UsersTable: FC<UsersTableProps> = (props) => {
  const {
    filters,
    users: { users },
    users: totalUsers,
    usageStats,
    onEditingUser,
    onFilterChange,
  } = useDashboard();

  const { t } = useTranslation();
  const [selectedRow, setSelectedRow] = useState<ExpandedIndex | undefined>(
    undefined
  );
  const useTable = useBreakpointValue({ base: false, md: true });


  const isFiltered = users.length !== totalUsers.total;

  const handleSort = (column: string) => {
    setStatsSort("");
    let newSort = filters.sort;
    if (newSort.includes(column)) {
      if (newSort.startsWith("-")) {
        newSort = "-created_at";
      } else {
        newSort = "-" + column;
      }
    } else {
      newSort = column;
    }
    onFilterChange({
      sort: newSort,
    });
  };
  const [statsSort, setStatsSort] = useState<string>("");

  const handleStatsSort = (column: string) => {
    if (statsSort.replace("-", "") === column) {
      if (statsSort.startsWith("-")) {
        setStatsSort(column);
      } else {
        setStatsSort("");
      }
    } else {
      setStatsSort("-" + column);
    }
  };

  const sortedUsers = useMemo(() => {
    if (!statsSort) return users;
    const desc = statsSort.startsWith("-");
    const key = statsSort.replace("-", "") as keyof UserUsageStat;
    return [...users].sort((a, b) => {
      const statA = usageStats.get(a.username);
      const statB = usageStats.get(b.username);
      const valA = statA ? (statA[key] as number) : (desc ? -1 : Infinity);
      const valB = statB ? (statB[key] as number) : (desc ? -1 : Infinity);
      return desc ? valB - valA : valA - valB;
    });
  }, [users, usageStats, statsSort]);

  const toggleAccordion = (index: number) => {
    setSelectedRow(index === selectedRow ? undefined : index);
  };

  return (
    <Box id="users-table" overflowX="auto" overscrollBehaviorX="contain">
      <Accordion
        allowMultiple
        display={{ base: "block", md: "none" }}
        index={selectedRow}
      >
        <Table orientation="vertical" zIndex="docked" {...props}>
          <Thead zIndex="docked" position="relative">
            <Tr>
              <Th
                minW="120px"
                pl={4}
                pr={4}
                cursor={"pointer"}
                onClick={handleSort.bind(null, "username")}
              >
                <HStack>
                  <span>{t("users")}</span>
                  <Sort sort={filters.sort} column="username" />
                </HStack>
              </Th>
              <Th
                minW="150px"
                px={2}
              >
                <Select
                  aria-label={t("usersTable.status")}
                  value={filters.status || ""}
                  onChange={handleStatusFilter}
                  size="xs"
                  fontSize="xs"
                  fontWeight="600"
                  textTransform="uppercase"
                >
                  <option value="">{t("usersTable.status")}: all</option>
                  <option value="active">active</option>
                  <option value="on_hold">on hold</option>
                  <option value="disabled">disabled</option>
                  <option value="limited">limited</option>
                  <option value="expired">expired</option>
                </Select>
              </Th>
              <Th
                minW="100px"
                cursor={"pointer"}
                pr={0}
                onClick={handleSort.bind(null, "used_traffic")}
              >
                <HStack>
                  <span>{t("usersTable.dataUsage")}</span>
                  <Sort sort={filters.sort} column="used_traffic" />
                </HStack>
              </Th>
              <Th
                minW="32px"
                w="32px"
                p={0}
                cursor={"pointer"}
              ></Th>
            </Tr>
          </Thead>
          <Tbody>
            {!useTable &&
              users?.map((user, i) => {
                return (
                  <Fragment key={user.username}>
                    <Tr
                      onClick={toggleAccordion.bind(null, i)}
                      cursor="pointer"
                    >
                      <Td
                        borderBottom={0}
                        minW="100px"
                        pl={4}
                        pr={4}
                        maxW="calc(100vw - 50px - 32px - 100px - 48px)"
                      >
                        <div className="flex-status">
                          <OnlineBadge lastOnline={user.online_at} />
                          <Text isTruncated>{user.username}</Text>
                        </div>
                      </Td>
                      <Td borderBottom={0} minW="50px" pl={0} pr={0}>
                        <StatusBadge
                          compact
                          showDetail={false}
                          expiryDate={user.expire}
                          status={user.status}
                        />
                      </Td>
                      <Td borderBottom={0} minW="100px" pr={0}>
                        <UsageSliderCompact
                          totalUsedTraffic={user.lifetime_used_traffic}
                          dataLimitResetStrategy={
                            user.data_limit_reset_strategy
                          }
                          used={user.used_traffic}
                          total={user.data_limit}
                          colorScheme={statusColors[user.status].bandWidthColor}
                        />
                      </Td>
                      <Td p={0} borderBottom={0} w="32px" minW="32px">
                        <AccordionArrowIcon
                          color="gray.400"
                          transition="transform .2s ease-out"
                          transform={
                            selectedRow === i ? "rotate(180deg)" : "0deg"
                          }
                        />
                      </Td>
                    </Tr>
                    <Tr
                      className="collapsible"
                      onClick={toggleAccordion.bind(null, i)}
                    >
                      <Td p={0} colSpan={4}>
                        <AccordionItem border={0}>
                          <AccordionButton display="none"></AccordionButton>
                          <AccordionPanel
                            border={0}
                            cursor="pointer"
                            px={6}
                            py={3}
                          >
                            <VStack justifyContent="space-between" spacing="4">
                              <VStack
                                alignItems="flex-start"
                                w="full"
                                spacing={-1}
                              >
                                <Text
                                  textTransform="uppercase"
                                  fontSize="xs"
                                  fontFamily="mono"
                                  letterSpacing="0.08em"
                                  color="gray.500"
                                >
                                  {t("usersTable.dataUsage")}
                                </Text>
                                <Box width="full" minW="230px">
                                  <UsageSlider
                                    totalUsedTraffic={
                                      user.lifetime_used_traffic
                                    }
                                    dataLimitResetStrategy={
                                      user.data_limit_reset_strategy
                                    }
                                    used={user.used_traffic}
                                    total={user.data_limit}
                                    colorScheme={
                                      statusColors[user.status].bandWidthColor
                                    }
                                  />
                                </Box>
                              </VStack>
                              {(() => {
                                const stat = usageStats.get(user.username);
                                if (!stat) return null;
                                return (
                                  <HStack w="full" justifyContent="space-between" spacing={3} align="start">
                                    {(
                                      [
                                        { key: "bytes_prev_hour" as const, speed: "speed_prev_hour" as const, label: t("usersTable.prevHour") },
                                        { key: "bytes_curr_hour" as const, speed: "speed_curr_hour" as const, label: t("usersTable.currHour") },
                                        { key: "bytes_today" as const, speed: "speed_today" as const, label: t("usersTable.today") },
                                      ]
                                    ).map(({ key, speed, label }) => (
                                      <VStack key={key} align="start" spacing={0} flex={1}>
                                        <Text fontSize="xs" fontFamily="mono" textTransform="uppercase" letterSpacing="0.08em" color="gray.500">
                                          {label}
                                        </Text>
                                        <Text fontSize="sm" fontFamily="mono">{formatBytes(stat[key])}</Text>
                                        <Text fontSize="xs" color="gray.500">
                                          {t("usersTable.avgSpeedPrefix")} {formatSpeed(stat[speed])}
                                        </Text>
                                      </VStack>
                                    ))}
                                  </HStack>
                                );
                              })()}
                              <HStack w="full" justifyContent="space-between">
                                <Box width="full">
                                  <StatusBadge
                                    compact
                                    expiryDate={user.expire}
                                    status={user.status}
                                  />
                                  <OnlineStatus lastOnline={user.online_at} />
                                </Box>
                                <HStack>
                                  <ActionButtons user={user} />
                                  <Tooltip
                                    label={t("userDialog.editUser")}
                                    placement="top"
                                  >
                                    <IconButton
                                      p="0 !important"
                                      aria-label="Edit user"
                                      size={{
                                        base: "sm",
                                        md: "md",
                                      }}
                                      {...actionButtonStyle}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        onEditingUser(user);
                                      }}
                                    >
                                      <EditIcon />
                                    </IconButton>
                                  </Tooltip>
                                </HStack>
                              </HStack>
                            </VStack>
                          </AccordionPanel>
                        </AccordionItem>
                      </Td>
                    </Tr>
                  </Fragment>
                );
              })}
          </Tbody>
        </Table>
      </Accordion>
      <Table
        orientation="vertical"
        display={{ base: "none", md: "table" }}
        tableLayout="fixed"
        minW="1090px"
        {...props}
      >
        <Thead>
          <Tr>
            <Th w="160px" cursor="pointer" onClick={handleSort.bind(null, "username")}>
              <HStack><span>{t("username")}</span><Sort sort={filters.sort} column="username" /></HStack>
            </Th>
            <Th w="150px" cursor="pointer" onClick={handleSort.bind(null, "expire")}>
              <HStack><span>{t("usersTable.status")}</span><Sort sort={filters.sort} column="expire" /></HStack>
            </Th>
            <Th w="260px" cursor="pointer" onClick={handleSort.bind(null, "used_traffic")}>
              <HStack><span>{t("usersTable.dataUsage")}</span><Sort sort={filters.sort} column="used_traffic" /></HStack>
            </Th>
            <Th w="120px" cursor="pointer" onClick={() => handleStatsSort("bytes_prev_hour")}>
              <HStack><span>{t("usersTable.prevHour")}</span><Sort sort={statsSort} column="bytes_prev_hour" /></HStack>
            </Th>
            <Th w="120px" cursor="pointer" onClick={() => handleStatsSort("bytes_curr_hour")}>
              <HStack><span>{t("usersTable.currHour")}</span><Sort sort={statsSort} column="bytes_curr_hour" /></HStack>
            </Th>
            <Th w="120px" cursor="pointer" onClick={() => handleStatsSort("bytes_today")}>
              <HStack><span>{t("usersTable.today")}</span><Sort sort={statsSort} column="bytes_today" /></HStack>
            </Th>
            <Th w="160px" />
          </Tr>
        </Thead>
        <Tbody>
          {useTable &&
            sortedUsers?.map((user, i) => {
              return (
                <Tr
                  key={user.username}
                  className={classNames("interactive", {
                    "last-row": i === sortedUsers.length - 1,
                  })}
                  onClick={() => onEditingUser(user)}
                >
                  <Td w="160px">
                    <div className="flex-status">
                      <OnlineBadge lastOnline={user.online_at} />
                      {user.username}
                      <OnlineStatus lastOnline={user.online_at} />
                    </div>
                  </Td>
                  <Td w="150px">
                    <StatusBadge
                      expiryDate={user.expire}
                      status={user.status}
                    />
                  </Td>
                  <Td w="260px">
                    <UsageSlider
                      totalUsedTraffic={user.lifetime_used_traffic}
                      dataLimitResetStrategy={user.data_limit_reset_strategy}
                      used={user.used_traffic}
                      total={user.data_limit}
                      colorScheme={statusColors[user.status].bandWidthColor}
                    />
                  </Td>
                  {(["bytes_prev_hour", "bytes_curr_hour", "bytes_today"] as const).map((key, idx) => {
                    const speedKeys = ["speed_prev_hour", "speed_curr_hour", "speed_today"] as const;
                    const stat = usageStats.get(user.username);
                    const bytes = stat ? stat[key] : null;
                    const speed = stat ? stat[speedKeys[idx]] : null;
                    return (
                      <Td key={key} w="120px">
                        {stat ? (
                          <VStack spacing={0} align="start">
                            <Text fontSize="sm" fontFamily="mono">{formatBytes(bytes!)}</Text>
                            <Text fontSize="xs" color="gray.500">
                              {t("usersTable.avgSpeedPrefix")} {formatSpeed(speed!)}
                            </Text>
                          </VStack>
                        ) : (
                          <Text color="gray.600">—</Text>
                        )}
                      </Td>
                    );
                  })}
                  <Td w="160px">
                    <ActionButtons user={user} />
                  </Td>
                </Tr>
              );
            })}
          {users.length == 0 && (
            <Tr>
              <Td colSpan={7}>
                <EmptySection isFiltered={isFiltered} />
              </Td>
            </Tr>
          )}
        </Tbody>
      </Table>
      <Pagination />
    </Box>
  );
};

type ActionButtonsProps = {
  user: User;
};

const ActionButtons: FC<ActionButtonsProps> = ({ user }) => {
  const { setQRCode, setSubLink } = useDashboard();

  const proxyLinks = user.links.join("\r\n");

  const [copied, setCopied] = useState([-1, false]);
  useEffect(() => {
    if (copied[1]) {
      setTimeout(() => {
        setCopied([-1, false]);
      }, 1000);
    }
  }, [copied]);
  return (
    <HStack
      justifyContent="flex-end"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
    >
      <CopyToClipboard
        text={
          user.subscription_url.startsWith("/")
            ? window.location.origin + user.subscription_url
            : user.subscription_url
        }
        onCopy={() => {
          setCopied([0, true]);
        }}
      >
        <div>
          <Tooltip
            label={
              copied[0] == 0 && copied[1]
                ? t("usersTable.copied")
                : t("usersTable.copyLink")
            }
            placement="top"
          >
            <IconButton
              p="0 !important"
              aria-label="copy subscription link"
              size={{
                base: "sm",
                md: "md",
              }}
              {...actionButtonStyle}
            >
              {copied[0] == 0 && copied[1] ? (
                <CopiedIcon />
              ) : (
                <SubscriptionLinkIcon />
              )}
            </IconButton>
          </Tooltip>
        </div>
      </CopyToClipboard>
      <CopyToClipboard
        text={proxyLinks}
        onCopy={() => {
          setCopied([1, true]);
        }}
      >
        <div>
          <Tooltip
            label={
              copied[0] == 1 && copied[1]
                ? t("usersTable.copied")
                : t("usersTable.copyConfigs")
            }
            placement="top"
          >
            <IconButton
              p="0 !important"
              aria-label="copy configs"
              size={{
                base: "sm",
                md: "md",
              }}
              {...actionButtonStyle}
            >
              {copied[0] == 1 && copied[1] ? <CopiedIcon /> : <CopyIcon />}
            </IconButton>
          </Tooltip>
        </div>
      </CopyToClipboard>
      <Tooltip label="QR Code" placement="top">
        <IconButton
          p="0 !important"
          aria-label="qr code"
          size={{
            base: "sm",
            md: "md",
          }}
          {...actionButtonStyle}
          onClick={() => {
            setQRCode(user.links);
            setSubLink(user.subscription_url);
          }}
        >
          <QRIcon />
        </IconButton>
      </Tooltip>
    </HStack>
  );
};

type EmptySectionProps = {
  isFiltered: boolean;
};

const EmptySection: FC<EmptySectionProps> = ({ isFiltered }) => {
  const { onCreateUser } = useDashboard();
  return (
    <Box
      padding="5"
      py="8"
      display="flex"
      alignItems="center"
      flexDirection="column"
      gap={4}
      w="full"
    >
      <EmptySectionIcon
        maxHeight="200px"
        maxWidth="200px"
        sx={{
          'path[fill="#fff"]': {
            fill: "terminal.overlay",
          },
          'path[fill="#f2f2f2"], path[fill="#e6e6e6"], path[fill="#ccc"]': {
            fill: "terminal.border",
          },
          'circle[fill="#3182CE"]': {
            fill: "primary.400",
          },
        }}
      />
      <Text fontFamily="mono" fontSize="sm" color="gray.400">
        {isFiltered ? t("usersTable.noUserMatched") : t("usersTable.noUser")}
      </Text>
      {!isFiltered && (
        <Button
          size="sm"
          colorScheme="primary"
          onClick={() => onCreateUser(true)}
        >
          {t("createUser")}
        </Button>
      )}
    </Box>
  );
};
