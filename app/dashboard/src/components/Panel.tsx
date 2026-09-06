import { Box, BoxProps, Flex, Text } from "@chakra-ui/react";
import { FC, PropsWithChildren, ReactNode } from "react";

export type PanelProps = {
  label?: string;
  actions?: ReactNode;
  compact?: boolean;
} & BoxProps;

/**
 * Shared terminal-style container used by every settings surface so panels
 * stay visually identical across pages.
 */
export const Panel: FC<PropsWithChildren<PanelProps>> = ({
  label,
  actions,
  compact = false,
  children,
  ...props
}) => (
  <Box
    borderWidth="1px"
    borderColor="terminal.border"
    bg="terminal.surface"
    borderRadius="4px"
    minW="0"
    boxShadow="panel"
    overflow="hidden"
    {...props}
  >
    {(label || actions) && (
      <Flex
        align="center"
        justify="space-between"
        gap="3"
        flexWrap="wrap"
        px={compact ? "3" : "4"}
        py={compact ? "1.5" : "2.5"}
        borderBottom="1px solid"
        borderColor="terminal.border"
        bg="terminal.overlay"
      >
        <Text
          fontFamily="mono"
          fontSize={compact ? "10px" : "xs"}
          fontWeight="500"
          textTransform="uppercase"
          letterSpacing={compact ? "0.1em" : "0.14em"}
          color="gray.400"
          overflowWrap="anywhere"
        >
          {label}
        </Text>
        {actions}
      </Flex>
    )}
    <Box p={compact ? "3" : { base: "3", md: "4" }} minW="0">{children}</Box>
  </Box>
);

export default Panel;
