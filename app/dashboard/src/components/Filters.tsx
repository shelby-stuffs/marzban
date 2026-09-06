import {
  BoxProps,
  Button,
  chakra,
  Grid,
  GridItem,
  HStack,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  InputRightElement,
  Select,
  Spinner,
} from "@chakra-ui/react";
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import classNames from "classnames";
import { useDashboard } from "contexts/DashboardContext";
import debounce from "lodash.debounce";
import React, { FC, useState } from "react";
import { useTranslation } from "react-i18next";

const iconProps = {
  baseStyle: {
    w: 4,
    h: 4,
  },
};

const SearchIcon = chakra(MagnifyingGlassIcon, iconProps);
const ClearIcon = chakra(XMarkIcon, iconProps);
export const ReloadIcon = chakra(ArrowPathIcon, iconProps);

export type FilterProps = {} & BoxProps;
const setSearchField = debounce((search: string) => {
  useDashboard.getState().onFilterChange({
    ...useDashboard.getState().filters,
    offset: 0,
    search,
  });
}, 300);

export const Filters: FC<FilterProps> = ({ ...props }) => {
  const { loading, filters, onFilterChange, refetchUsers, onCreateUser } =
    useDashboard();
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setSearchField(e.target.value);
  };
  const clear = () => {
    setSearch("");
    onFilterChange({
      ...filters,
      offset: 0,
      search: "",
    });
  };
  return (
    <Grid
      id="filters"
      templateColumns={{
        lg: "minmax(260px, 1fr) 190px auto",
        md: "minmax(240px, 1fr) 180px auto",
        base: "1fr",
      }}
      position="sticky"
      top={0}
      mx="-6"
      px="6"
      rowGap={3}
      gap={{
        lg: 3,
        base: 0,
      }}
      bg="terminal.bg"
      borderBottom="1px solid"
      borderColor="terminal.border"
      py={3}
      zIndex="docked"
      {...props}
    >
      <GridItem order={{ base: 2, md: 1 }}>
        <InputGroup size="sm">
          <InputLeftElement
            pointerEvents="none"
            color="gray.500"
            children={<SearchIcon />}
          />
          <Input
            placeholder={t("search")}
            value={search}
            fontFamily="mono"
            onChange={onChange}
          />

          <InputRightElement>
            {loading && <Spinner size="xs" color="primary.400" />}
            {filters.search && filters.search.length > 0 && (
              <IconButton
                onClick={clear}
                aria-label="clear"
                size="xs"
                variant="ghost"
              >
                <ClearIcon />
              </IconButton>
            )}
          </InputRightElement>
        </InputGroup>
      </GridItem>
      <GridItem order={{ base: 3, md: 2 }}>
        <Select
          size="sm"
          aria-label={t("usersTable.status")}
          value={filters.status || ""}
          onChange={(event) =>
            onFilterChange({
              ...filters,
              offset: 0,
              status: event.target.value || undefined,
            })
          }
        >
          <option value="">— {t("usersTable.status")} —</option>
          <option value="active">{t("status.active")}</option>
          <option value="on_hold">{t("userDialog.onHold")}</option>
          <option value="disabled">{t("status.disabled")}</option>
          <option value="limited">{t("status.limited")}</option>
          <option value="expired">{t("status.expired")}</option>
        </Select>
      </GridItem>
      <GridItem order={{ base: 1, md: 3 }}>
        <HStack justifyContent="flex-end" alignItems="center" h="full" gap="2">
          <IconButton
            aria-label="refresh users"
            disabled={loading}
            onClick={refetchUsers}
            size="sm"
            variant="outline"
          >
            <ReloadIcon
              className={classNames({
                "animate-spin": loading,
              })}
            />
          </IconButton>
          <Button
            colorScheme="primary"
            size="sm"
            onClick={() => onCreateUser(true)}
            px={4}
          >
            {t("createUser")}
          </Button>
        </HStack>
      </GridItem>
    </Grid>
  );
};
