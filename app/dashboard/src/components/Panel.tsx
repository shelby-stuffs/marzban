import { Box, BoxProps, Flex, Text } from "@chakra-ui/react";
import { FC, PropsWithChildren, ReactNode } from "react";

export type PanelProps = {
  label?: string;
  actions?: ReactNode;
} & BoxProps;

/**
 * Shared terminal-style container used by every settings surface so panels
 * stay visually identical across pages.
 */
export const Panel: FC<PropsWithChildren<PanelProps>> = ({
  label,
  actions,
  children,
  ...props
}) => (
  <Box
    borderWidth="1px"
    borderColor="terminal.border"
    bg="terminal.surface"
    borderRadius="6px"
    boxShadow="panel"
    overflow="hidden"
    {...props}
  >
    {(label || actions) && (
      <Flex
        align="center"
        justify="space-between"
        gap="3"
        px="4"
        py="2.5"
        borderBottom="1px solid"
        borderColor="terminal.border"
        bg="terminal.overlay"
      >
        <Text
          fontFamily="mono"
          fontSize="10px"
          fontWeight="500"
          textTransform="uppercase"
          letterSpacing="0.14em"
          color="gray.400"
          noOfLines={1}
        >
          {label}
        </Text>
        {actions}
      </Flex>
    )}
    <Box p="4">{children}</Box>
  </Box>
);

export default Panel;
