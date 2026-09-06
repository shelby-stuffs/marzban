from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("singbox_config",ROOT/"app/singbox/config.py")
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def source_config():
    return {
      "inbounds":[
        {"tag":"hy2-main","protocol":"hysteria","listen":"0.0.0.0","port":443,
         "settings":{"clients":[]},
         "streamSettings":{"method":"hysteria","security":"tls",
          "hysteriaSettings":{"version":2},
          "tlsSettings":{"alpn":["h3"],"certificates":[{"certificateFile":"/cert.pem","keyFile":"/key.pem"}]},
          "finalmask":{"udp":[{"type":"salamander","settings":{"password":"server-mask"}}]}}},
        {"tag":"vless","protocol":"vless","port":8443,"settings":{"clients":[]}}
      ],
      "outbounds":[{"tag":"direct","protocol":"freedom"}],
      "routing":{"rules":[
        {"type":"field","inboundTag":["hy2-main"],"outboundTag":"direct"},
        {"type":"field","inboundTag":["hy2-main","vless"],"outboundTag":"direct"}]}}

class SingBoxSplitTests(unittest.TestCase):
 def test_xray_runtime_has_no_hysteria(self):
  result=module.strip_hysteria_from_xray(source_config())
  self.assertEqual([i["tag"] for i in result["inbounds"]],["vless"])
  self.assertEqual(len(result["routing"]["rules"]),1)
  self.assertEqual(result["routing"]["rules"][0]["inboundTag"],["vless"])

 def test_builds_native_singbox_hysteria_server(self):
  result=module.build_hysteria2_server_config(source_config(),{"hy2-main":[
    {"name":"7.alice","password":"user-auth","obfs_password":"must-not-leak"}]})
  inbound=result["inbounds"][0]
  self.assertEqual(inbound["type"],"hysteria2")
  self.assertEqual(inbound["listen_port"],443)
  self.assertEqual(inbound["users"],[{"name":"7.alice","password":"user-auth"}])
  self.assertEqual(inbound["obfs"],{"type":"salamander","password":"server-mask"})
  self.assertEqual(inbound["tls"]["certificate_path"],"/cert.pem")
  self.assertEqual(result["route"]["final"],"direct")

 def test_missing_server_certificate_is_rejected(self):
  source=source_config(); source["inbounds"][0]["streamSettings"]["tlsSettings"]={}
  with self.assertRaisesRegex(ValueError,"certificate"):
   module.build_hysteria2_server_config(source,{})

 def test_no_hysteria_produces_empty_singbox_inbounds(self):
  source=source_config(); source["inbounds"]=source["inbounds"][1:]
  self.assertEqual(module.build_hysteria2_server_config(source,{})["inbounds"],[])

if __name__=='__main__': unittest.main()
