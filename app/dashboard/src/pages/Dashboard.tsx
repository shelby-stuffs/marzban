import { Box } from "@chakra-ui/react";
import { Filters } from "components/Filters";
import { Footer } from "components/Footer";
import { Header } from "components/Header";
import { UsersTable } from "components/UsersTable";
import {
  fetchInbounds,
  fetchSingBoxInbounds,
  useDashboard,
} from "contexts/DashboardContext";
import { FC, useEffect } from "react";

export const Dashboard: FC = () => {
  useEffect(() => {
    useDashboard.getState().refetchUsers();
    fetchInbounds();
    fetchSingBoxInbounds();
  }, []);
  return (
    <Box w="full">
      <Header />
      <Filters />
      <UsersTable />
      <Box mt="4">
        <Footer />
      </Box>
    </Box>
  );
};

export default Dashboard;
