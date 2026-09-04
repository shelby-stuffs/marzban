from app.routers import api_router
from app.routers.wireguard import WireGuardServerRequest
from app.utils.crypto import generate_wireguard_keypair
from config import XRAY_SUBSCRIPTION_PATH


def test_server_request_builds_validated_wireguard_config():
    private_key, public_key = generate_wireguard_keypair()
    request = WireGuardServerRequest(
        endpoint_address="vpn.example.com",
        interface_name="wg0",
        private_key=private_key,
        listen_port=51820,
        address=["10.70.0.1/24"],
    )

    config = request.wireguard_config()

    assert config["public_key"] == public_key
    assert config["interface_name"] == "wg0"
    assert config["address"] == ["10.70.0.1/24"]


def test_wireguard_subscription_route_precedes_generic_client_route():
    paths = [route.path for route in api_router.routes]
    wireguard_path = f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/wireguard"
    generic_path = f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/{{client_type}}"

    assert wireguard_path in paths
    assert generic_path in paths
    assert paths.index(wireguard_path) < paths.index(generic_path)
