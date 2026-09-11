import { Box, Button, HStack, SimpleGrid, Text, useToast, VStack } from "@chakra-ui/react";
import { Header } from "components/Header";
import { Panel } from "components/Panel";
import { useDashboardTheme } from "contexts/ThemeContext";
import { ThemeDefinition } from "theme/themes";

const ThemeCard = ({ item, active, disabled, onSelect }: { item: ThemeDefinition; active: boolean; disabled: boolean; onSelect: () => void }) => (
  <Button
    variant="outline" h="auto" minH="152px" p="4" whiteSpace="normal" textAlign="left"
    borderColor={active ? "primary.500" : "terminal.border"} bg={active ? "var(--theme-active-soft)" : "terminal.surface"}
    boxShadow={active ? "glow" : "none"} onClick={onSelect} isDisabled={disabled} aria-pressed={active}
  >
    <VStack align="stretch" spacing="3" w="full">
      <HStack spacing="2">
        {item.preview.map((color) => <Box key={color} boxSize="7" borderRadius="full" bg={color} border="1px solid" borderColor="blackAlpha.300" />)}
      </HStack>
      <Box>
        <Text fontFamily="heading" fontWeight="700" color={active ? "primary.300" : "terminal.text"}>{item.name}</Text>
        <Text mt="1" fontSize="xs" color="gray.400" lineHeight="1.5">{item.description}</Text>
      </Box>
      <Text fontSize="10px" fontFamily="mono" textTransform="uppercase" letterSpacing="0.1em" color={active ? "primary.300" : "gray.500"}>
        {active ? "active / synced" : "select theme"}
      </Text>
    </VStack>
  </Button>
);

export const AppearanceSettingsPage = () => {
  const { theme, themes, saving, selectTheme } = useDashboardTheme();
  const toast = useToast();
  const choose = async (id: ThemeDefinition["id"]) => {
    if (id === theme) return;
    try {
      await selectTheme(id);
      toast({ title: "Theme saved for your account", status: "success", position: "top", duration: 2500 });
    } catch (error: any) {
      toast({ title: error?.response?._data?.detail || "Could not save theme", status: "error", position: "top" });
    }
  };
  return (
    <VStack align="stretch" spacing="4">
      <Header title="Appearance" />
      <Panel label="theme combiner">
        <Text mb="4" color="gray.400" fontSize="sm">Choose a dashboard style. The preference follows your administrator account on every device.</Text>
        <SimpleGrid columns={{ base: 1, sm: 2, xl: 4 }} spacing="4">
          {themes.map((item) => <ThemeCard key={item.id} item={item} active={item.id === theme} disabled={saving} onSelect={() => void choose(item.id)} />)}
        </SimpleGrid>
      </Panel>
    </VStack>
  );
};

export default AppearanceSettingsPage;
