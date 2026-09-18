from app.subscription.hysteria2 import Hysteria2Client
from copy import deepcopy

import copy
import json
from random import choice

from app.utils.helpers import UUIDEncoder
from jinja2.exceptions import TemplateNotFound

from app.subscription.funcs import get_grpc_gun
from app.templates import render_template
from config import (
    MUX_TEMPLATE,
    SINGBOX_SETTINGS_TEMPLATE,
    SINGBOX_SUBSCRIPTION_TEMPLATE,
    USER_AGENT_TEMPLATE
)


class SingBoxConfiguration(str):

    def __init__(self):
        self.proxy_remarks = []
        self.config = json.loads(render_template(SINGBOX_SUBSCRIPTION_TEMPLATE))
        self.mux_template = render_template(MUX_TEMPLATE)
        user_agent_data = json.loads(render_template(USER_AGENT_TEMPLATE))

        if 'list' in user_agent_data and isinstance(user_agent_data['list'], list):
            self.user_agent_list = user_agent_data['list']
        else:
            self.user_agent_list = []

        try:
            self.settings = json.loads(render_template(SINGBOX_SETTINGS_TEMPLATE))
        except TemplateNotFound:
            self.settings = {}

        del user_agent_data

    def _remark_validation(self, remark):
        if not remark in self.proxy_remarks:
            return remark
        c = 2
        while True:
            new = f'{remark} ({c})'
            if not new in self.proxy_remarks:
                return new
            c += 1

    def add_outbound(self, outbound_data):
        self.config["outbounds"].append(outbound_data)

    @staticmethod
    def _proxy_settings(proxies, protocol: str):
        for proxy_type, settings in proxies.items():
            if getattr(proxy_type, "value", proxy_type) == protocol:
                return settings
        return None

    @staticmethod
    def _client_tls(server_tls, address: str) -> dict:
        if not isinstance(server_tls, dict) or not server_tls.get("enabled"):
            return {}
        tls = {"enabled": True, "server_name": server_tls.get("server_name") or address}
        for key in ("insecure", "alpn", "min_version", "max_version"):
            if key in server_tls:
                tls[key] = deepcopy(server_tls[key])
        if isinstance(server_tls.get("reality"), dict):
            tls["reality"] = deepcopy(server_tls["reality"])
        if isinstance(server_tls.get("utls"), dict):
            tls["utls"] = deepcopy(server_tls["utls"])
        return tls

    def add_custom_inbounds(self, proxies, format_variables, advanced_config=None):
        """Expose configured sing-box server inbounds as client outbounds."""
        if advanced_config is None:
            return
        protocol_map = {
            "vless": "vless",
            "vmess": "vmess",
            "trojan": "trojan",
            "shadowsocks": "shadowsocks",
            "hysteria2": "hysteria2",
        }
        address = format_variables.get("SERVER_IP")
        if not address:
            return
        for inbound in advanced_config.get("inbounds", []):
            if not isinstance(inbound, dict):
                continue
            protocol = protocol_map.get(inbound.get("type"))
            tag = inbound.get("tag")
            port = inbound.get("listen_port")
            settings = self._proxy_settings(proxies, protocol) if protocol else None
            if not protocol or not isinstance(tag, str) or not tag or not settings:
                continue
            if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
                continue

            user_settings = settings.model_dump() if hasattr(settings, "model_dump") else dict(settings)
            remark = self._remark_validation(
                f"{format_variables.get('USERNAME', '{USERNAME}')} [{protocol} / {tag}]"
            )
            outbound = {
                "type": protocol,
                "tag": remark,
                "server": address,
                "server_port": port,
            }
            if protocol in ("vless", "vmess"):
                if not user_settings.get("id"):
                    continue
                outbound["uuid"] = user_settings["id"]
            elif protocol == "trojan":
                if not user_settings.get("password"):
                    continue
                outbound["password"] = user_settings["password"]
            elif protocol == "shadowsocks":
                if not user_settings.get("password"):
                    continue
                outbound["password"] = user_settings["password"]
                outbound["method"] = user_settings.get("method", "chacha20-ietf-poly1305")
            elif protocol == "hysteria2":
                if not user_settings.get("auth"):
                    continue
                outbound["password"] = user_settings["auth"]

            if isinstance(inbound.get("tls"), dict):
                tls = self._client_tls(inbound["tls"], address)
                if tls:
                    outbound["tls"] = tls
            if isinstance(inbound.get("transport"), dict):
                outbound["transport"] = deepcopy(inbound["transport"])
            if isinstance(inbound.get("multiplex"), dict):
                outbound["multiplex"] = deepcopy(inbound["multiplex"])
            if protocol == "hysteria2" and isinstance(inbound.get("obfs"), dict):
                outbound["obfs"] = deepcopy(inbound["obfs"])
            self.add_outbound(outbound)

    def render(self, reverse=False):
        urltest_types = ["vmess", "vless", "trojan", "shadowsocks", "hysteria2", "tuic", "http", "ssh"]
        urltest_tags = [outbound["tag"]
                        for outbound in self.config["outbounds"] if outbound["type"] in urltest_types]
        selector_types = ["vmess", "vless", "trojan", "shadowsocks", "hysteria2", "tuic", "http", "ssh", "urltest"]
        selector_tags = [outbound["tag"]
                         for outbound in self.config["outbounds"] if outbound["type"] in selector_types]

        for outbound in self.config["outbounds"]:
            if outbound.get("type") == "urltest":
                outbound["outbounds"] = urltest_tags

        for outbound in self.config["outbounds"]:
            if outbound.get("type") == "selector":
                outbound["outbounds"] = selector_tags

        if reverse:
            self.config["outbounds"].reverse()
        return json.dumps(self.config, indent=4,cls=UUIDEncoder)

    @staticmethod
    def tls_config(sni=None, fp=None, tls=None, pbk=None,
                   sid=None, alpn=None, ais=None):

        config = {}
        if tls in ['tls', 'reality']:
            config["enabled"] = True

        if sni is not None:
            config["server_name"] = sni

        if tls == 'tls' and ais:
            config['insecure'] = ais

        if tls == 'reality':
            config["reality"] = {"enabled": True}
            if pbk:
                config["reality"]["public_key"] = pbk
            if sid:
                config["reality"]["short_id"] = sid

        if fp:
            config["utls"] = {
                "enabled": bool(fp),
                "fingerprint": fp
            }

        if alpn:
            config["alpn"] = [alpn] if not isinstance(alpn, list) else alpn

        return config

    def http_config(self, host='', path='', random_user_agent: bool = False):
        config = copy.deepcopy(self.settings.get("httpSettings", {
            "idle_timeout": "15s",
            "ping_timeout": "15s",
            "method": "GET",
            "headers": {}
        }))
        if "headers" not in config:
            config["headers"] = {}

        config["host"] = []
        if path:
            config["path"] = path
        if host:
            config["host"] = [host]
        if random_user_agent:
            config["headers"]["User-Agent"] = choice(self.user_agent_list)

        return config

    def ws_config(self, host='', path='', random_user_agent: bool = False,
                  max_early_data=None, early_data_header_name=None):
        config = copy.deepcopy(self.settings.get("wsSettings", {
            "headers": {}
        }))
        if "headers" not in config:
            config["headers"] = {}

        if path:
            config["path"] = path
        if host:
            config["headers"]["Host"] = host
        if random_user_agent:
            config["headers"]["User-Agent"] = choice(self.user_agent_list)
        if max_early_data is not None:
            config["max_early_data"] = max_early_data
        if early_data_header_name:
            config["early_data_header_name"] = early_data_header_name

        return config

    def grpc_config(self, path=''):
        config = copy.deepcopy(self.settings.get("grpcSettings", {}))

        if path:
            config["service_name"] = path

        return config

    def httpupgrade_config(self, host='', path='', random_user_agent: bool = False):
        config = copy.deepcopy(self.settings.get("httpupgradeSettings", {
            "headers": {}
        }))
        if "headers" not in config:
            config["headers"] = {}

        config["host"] = host
        if path:
            config["path"] = path
        if random_user_agent:
            config["headers"]["User-Agent"] = choice(self.user_agent_list)

        return config

    def transport_config(self,
                         transport_type='',
                         host='',
                         path='',
                         max_early_data=None,
                         early_data_header_name=None,
                         random_user_agent: bool = False,
                         ):

        transport_config = {}

        if transport_type:
            if transport_type == "http":
                transport_config = self.http_config(
                    host=host,
                    path=path,
                    random_user_agent=random_user_agent,
                )

            elif transport_type == "ws":
                transport_config = self.ws_config(
                    host=host,
                    path=path,
                    random_user_agent=random_user_agent,
                    max_early_data=max_early_data,
                    early_data_header_name=early_data_header_name,
                )

            elif transport_type == "grpc":
                transport_config = self.grpc_config(path=path)

            elif transport_type == "httpupgrade":
                transport_config = self.httpupgrade_config(
                    host=host,
                    path=path,
                    random_user_agent=random_user_agent,
                )

        transport_config['type'] = transport_type
        return transport_config

    def make_outbound(self,
                      type: str,
                      remark: str,
                      address: str,
                      port: int,
                      net='',
                      path='',
                      host='',
                      flow='',
                      tls='',
                      sni='',
                      fp='',
                      alpn='',
                      pbk='',
                      sid='',
                      headers='',
                      ais='',
                      mux_enable: bool = False,
                      random_user_agent: bool = False,
                      ):

        if isinstance(port, str):
            ports = port.split(',')
            port = int(choice(ports))

        config = {
            "type": type,
            "tag": remark,
            "server": address,
            "server_port": port,
        }

        if (
            net in ('tcp', 'raw', 'kcp')
            and headers != 'http'
            and tls in ('tls', 'reality')
            and flow
        ):
            config["flow"] = flow

        if net == 'h2':
            net = 'http'
            alpn = 'h2'
        elif net == 'h3':
            net = 'http'
            alpn = 'h3'
        elif net in ['tcp', 'raw'] and headers == 'http':
            net = 'http'

        if net in ['http', 'ws', 'quic', 'grpc', 'httpupgrade']:
            max_early_data = None
            early_data_header_name = None

            if "?ed=" in path:
                path, max_early_data = path.split("?ed=")
                max_early_data, = max_early_data.split("/")
                max_early_data = int(max_early_data)
                early_data_header_name = "Sec-WebSocket-Protocol"

            config['transport'] = self.transport_config(
                transport_type=net,
                host=host,
                path=path,
                max_early_data=max_early_data,
                early_data_header_name=early_data_header_name,
                random_user_agent=random_user_agent,
            )

        if tls in ('tls', 'reality'):
            config['tls'] = self.tls_config(sni=sni, fp=fp, tls=tls,
                                            pbk=pbk, sid=sid, alpn=alpn,
                                            ais=ais)

        mux_json = json.loads(self.mux_template)
        mux_config = mux_json["sing-box"]

        config['multiplex'] = mux_config
        if config['multiplex']["enabled"]:
            config['multiplex']["enabled"] = mux_enable

        return config

    def add(self, remark: str, address: str, inbound: dict, settings: dict):

        net = inbound["network"]
        path = inbound["path"]

        # The same validated profile drives every native Hysteria2 format.
        if inbound["protocol"] == "hysteria":
            profile = Hysteria2Client.from_mapping(address, inbound, settings)
            remark = self._remark_validation(remark)
            self.proxy_remarks.append(remark)
            self.add_outbound(profile.singbox(remark))
            return

        # not supported by sing-box
        if net in ("kcp", "splithttp", "xhttp", "hysteria") or (net == "quic" and inbound["header_type"] != "none"):
            return

        if net in ("grpc", "gun"):
            path = get_grpc_gun(path)

        alpn = inbound.get('alpn', None)

        remark = self._remark_validation(remark)
        self.proxy_remarks.append(remark)

        outbound = self.make_outbound(
            remark=remark,
            type=inbound['protocol'],
            address=address,
            port=inbound['port'],
            net=net,
            tls=(inbound['tls']),
            flow=settings.get('flow', ''),
            sni=inbound['sni'],
            host=inbound['host'],
            path=path,
            alpn=alpn.rsplit(sep=",") if alpn else None,
            fp=inbound.get('fp', ''),
            pbk=inbound.get('pbk', ''),
            sid=inbound.get('sid', ''),
            headers=inbound['header_type'],
            ais=inbound.get('ais', ''),
            mux_enable=inbound.get('mux_enable', False),
            random_user_agent=inbound.get('random_user_agent', False),)

        if inbound['protocol'] == 'vmess':
            outbound['uuid'] = settings['id']

        elif inbound['protocol'] == 'vless':
            outbound['uuid'] = settings['id']

        elif inbound['protocol'] == 'trojan':
            outbound['password'] = settings['password']

        elif inbound['protocol'] == 'shadowsocks':
            outbound['password'] = settings['password']
            outbound['method'] = settings['method']

        self.add_outbound(outbound)
