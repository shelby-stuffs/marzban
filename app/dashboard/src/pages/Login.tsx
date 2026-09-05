import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  chakra,
  Flex,
  FormControl,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react";
import { ArrowRightOnRectangleIcon } from "@heroicons/react/24/outline";
import { zodResolver } from "@hookform/resolvers/zod";
import { FC, useEffect, useState } from "react";
import { FieldValues, useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Footer } from "components/Footer";
import { Input } from "components/Input";
import { fetch } from "service/http";
import { removeAuthToken, setAuthToken } from "utils/authStorage";
import { ReactComponent as Logo } from "assets/logo.svg";
import { useTranslation } from "react-i18next";
import { Language } from "components/Language";

const schema = z.object({
  username: z.string().min(1, "login.fieldRequired"),
  password: z.string().min(1, "login.fieldRequired"),
});

export const LogoIcon = chakra(Logo, {
  baseStyle: {
    strokeWidth: "10px",
    w: 10,
    h: 10,
  },
});

const LoginIcon = chakra(ArrowRightOnRectangleIcon, {
  baseStyle: {
    w: 4,
    h: 4,
    strokeWidth: "2px",
  },
});

export const Login: FC = () => {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();
  let location = useLocation();
  const {
    register,
    formState: { errors },
    handleSubmit,
  } = useForm({
    resolver: zodResolver(schema),
  });
  useEffect(() => {
    removeAuthToken();
    if (location.pathname !== "/login") {
      navigate("/login", { replace: true });
    }
  }, []);
  const login = (values: FieldValues) => {
    setError("");
    const formData = new FormData();
    formData.append("username", values.username);
    formData.append("password", values.password);
    formData.append("grant_type", "password");
    setLoading(true);
    fetch("/admin/token", { method: "post", body: formData })
      .then(({ access_token: token }) => {
        setAuthToken(token);
        navigate("/");
      })
      .catch((err) => {
        setError(err.response._data.detail);
      })
      .finally(setLoading.bind(null, false));
  };
  return (
    <VStack justifyContent="space-between" minH="100vh" p="6" w="full">
      <Box w="full">
        <HStack justifyContent="end" w="full">
          <Language />
        </HStack>
        <Flex w="full" justifyContent="center" mt={{ base: "8", md: "16" }}>
          <Box
            w="full"
            maxW="360px"
            borderWidth="1px"
            borderColor="terminal.border"
            bg="terminal.surface"
            borderRadius="6px"
            boxShadow="panel"
            overflow="hidden"
          >
            <HStack
              px="4"
              py="2.5"
              spacing="2"
              borderBottom="1px solid"
              borderColor="terminal.border"
              bg="terminal.overlay"
            >
              <Box
                boxSize="2"
                borderRadius="1px"
                bg="primary.500"
                boxShadow="glow"
              />
              <Text
                fontFamily="mono"
                fontSize="10px"
                textTransform="uppercase"
                letterSpacing="0.14em"
                color="gray.400"
              >
                marzban / auth
              </Text>
            </HStack>

            <Box p="6">
              <VStack alignItems="center" w="full" spacing="1">
                <Box color="primary.400" mb="1">
                  <LogoIcon />
                </Box>
                <Text fontFamily="mono" fontSize="lg" fontWeight="600">
                  {t("login.loginYourAccount")}
                </Text>
                <Text fontSize="sm" color="gray.500">
                  {t("login.welcomeBack")}
                </Text>
              </VStack>
              <Box w="full" pt="5">
                <form onSubmit={handleSubmit(login)}>
                  <VStack rowGap={3}>
                    <FormControl>
                      <Input
                        w="full"
                        placeholder={t("username")}
                        {...register("username")}
                        error={t(errors?.username?.message as string)}
                      />
                    </FormControl>
                    <FormControl>
                      <Input
                        w="full"
                        type="password"
                        placeholder={t("password")}
                        {...register("password")}
                        error={t(errors?.password?.message as string)}
                      />
                    </FormControl>
                    {error && (
                      <Alert status="error" rounded="md">
                        <AlertIcon />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}
                    <Button
                      isLoading={loading}
                      type="submit"
                      w="full"
                      colorScheme="primary"
                    >
                      {<LoginIcon marginRight={2} />}
                      {t("login")}
                    </Button>
                  </VStack>
                </form>
              </Box>
            </Box>
          </Box>
        </Flex>
      </Box>
      <Footer />
    </VStack>
  );
};

export default Login;
