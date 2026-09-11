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
    borderColor="rgba(255, 188, 226, 0.20)"
    bg="rgba(29, 17, 31, 0.84)"
    backdropFilter="blur(18px) saturate(130%)"
    borderRadius="16px"
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
        borderColor="rgba(255, 188, 226, 0.16)"
        bg="linear-gradient(90deg, rgba(246,83,173,.13), rgba(189,145,255,.07))"
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
