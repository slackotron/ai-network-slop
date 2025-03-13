from nornir import InitNornir
from nornir_napalm.plugins.tasks import napalm_get
from nornir_utils.plugins.functions import print_result
from ciscoconfparse2 import CiscoConfParse
from typing import Dict, List
import os
from datetime import datetime

class AristaConfigAuditor:
    def __init__(self):
        """Initialize Nornir and configuration settings."""
        self.nr = InitNornir(
            config_file="config.yaml",
            logging={"enabled": False}
        )

    def get_configs(self) -> Dict[str, str]:
        """
        Fetch running configurations from all Arista devices.
        
        Returns:
            Dictionary mapping hostname to configuration
        """
        # Run NAPALM get_config task
        result = self.nr.run(
            task=napalm_get,
            getters=["config"],
        )

        configs = {}
        for host, host_data in result.items():
            if not host_data.failed:
                configs[host] = host_data.result["config"]["running"]
            else:
                print(f"Failed to get config from {host}: {host_data.exception}")

        return configs

    def audit_config(self, config: str) -> Dict[str, List[str]]:
        """
        Audit a single configuration for security and best practices.
        
        Args:
            config: Device configuration as string
            
        Returns:
            Dictionary of findings by category
        """
        parse = CiscoConfParse(config.splitlines(), syntax='eos')
        findings = {
            "Management Security": self._check_management_security(parse),
            "VXLAN Configuration": self._check_vxlan_config(parse),
            "Interface Security": self._check_interface_security(parse),
            "Routing Security": self._check_routing_security(parse),
            "System Security": self._check_system_security(parse),
        }
        return findings

    def _check_management_security(self, parse: CiscoConfParse) -> List[str]:
        """Check management plane security configurations."""
        findings = []
        
        # Check Management VRF
        mgmt_intf = parse.find_objects(r"^interface Management")
        if mgmt_intf and not any("vrf MGMT" in line.text for line in mgmt_intf[0].children):
            findings.append("Management interface not in dedicated VRF")

        # Check SSH Version and Ciphers
        ssh_config = parse.find_objects(r"^management ssh")
        if not ssh_config:
            findings.append("SSH configuration not found")
        else:
            if not any("cipher" in line.text for line in ssh_config[0].children):
                findings.append("SSH ciphers not explicitly configured")

        # Check for ACLs on Management Interface
        if mgmt_intf and not any("access-group" in line.text for line in mgmt_intf[0].children):
            findings.append("No ACL applied to management interface")

        return findings

    def _check_vxlan_config(self, parse: CiscoConfParse) -> List[str]:
        """Check VXLAN configuration if present."""
        findings = []
        
        vxlan_intf = parse.find_objects(r"^interface Vxlan1")
        if vxlan_intf:
            if not any("source-interface" in line.text for line in vxlan_intf[0].children):
                findings.append("VXLAN source-interface not configured")
            
            if not any("vlan" in line.text and "vni" in line.text 
                      for line in vxlan_intf[0].children):
                findings.append("No VXLAN VNI to VLAN mappings found")

            # Check for EVPN configuration
            if not parse.find_objects(r"^router bgp.*evpn"):
                findings.append("EVPN not configured for VXLAN")

        return findings

    def _check_interface_security(self, parse: CiscoConfParse) -> List[str]:
        """Check interface security configurations."""
        findings = []
        
        for intf in parse.find_objects(r"^interface Ethernet"):
            # Skip shutdown interfaces
            if any("shutdown" in line.text for line in intf.children):
                continue

            # Check storm control
            if not any("storm-control" in line.text for line in intf.children):
                findings.append(f"{intf.text} - Storm control not configured")

            # Check port security on access ports
            if (any("switchport mode access" in line.text for line in intf.children) and
                not any("port-security" in line.text for line in intf.children)):
                findings.append(f"{intf.text} - Port security not enabled on access port")

            # Check BPDU guard
            if (any("switchport mode access" in line.text for line in intf.children) and
                not any("spanning-tree bpduguard enable" in line.text 
                       for line in intf.children)):
                findings.append(f"{intf.text} - BPDU guard not enabled on access port")

        return findings

    def _check_routing_security(self, parse: CiscoConfParse) -> List[str]:
        """Check routing protocol security configurations."""
        findings = []
        
        bgp_config = parse.find_objects(r"^router bgp")
        if bgp_config:
            # Check for peer groups
            if not any("peer-group" in line.text for line in bgp_config[0].children):
                findings.append("BGP peer groups not utilized")

            # Check for password authentication
            if not any("password" in line.text for line in bgp_config[0].children):
                findings.append("BGP authentication not configured")

            # Check for BFD
            if not any("bfd" in line.text for line in bgp_config[0].children):
                findings.append("BFD not enabled for BGP")

        return findings

    def _check_system_security(self, parse: CiscoConfParse) -> List[str]:
        """Check system-wide security settings."""
        findings = []
        
        # Check AAA
        if not parse.find_objects(r"^aaa authentication"):
            findings.append("AAA authentication not configured")
        
        # Check NTP
        if not parse.find_objects(r"^ntp server"):
            findings.append("NTP not configured")
        
        # Check logging
        if not parse.find_objects(r"^logging host"):
            findings.append("Remote logging not configured")
        
        # Check TACACS/RADIUS
        if not (parse.find_objects(r"^tacacs") or parse.find_objects(r"^radius")):
            findings.append("Neither TACACS+ nor RADIUS configured")

        return findings

    def run_audit(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Run full audit on all devices.
        
        Returns:
            Dictionary mapping hostname to audit findings
        """
        configs = self.get_configs()
        results = {}
        
        for hostname, config in configs.items():
            results[hostname] = self.audit_config(config)
            
        return results

    def save_results(self, results: Dict[str, Dict[str, List[str]]], 
                    filename: str = None) -> None:
        """Save audit results to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_results_{timestamp}.txt"
            
        with open(filename, 'w') as f:
            f.write("Arista Network Configuration Audit Results\n")
            f.write("========================================\n\n")
            
            for hostname, categories in results.items():
                f.write(f"Device: {hostname}\n")
                f.write("-" * (len(hostname) + 8) + "\n")
                
                for category, findings in categories.items():
                    if findings:
                        f.write(f"\n{category}:\n")
                        for finding in findings:
                            f.write(f"  - {finding}\n")
                f.write("\n\n")

def main():
    """Main function to run the audit."""
    # Initialize the auditor
    auditor = AristaConfigAuditor()
    
    # Run the audit
    print("Starting configuration audit...")
    results = auditor.run_audit()
    
    # Save results
    auditor.save_results(results)
    
    # Print summary
    print("\nAudit Summary:")
    for hostname, categories in results.items():
        total_findings = sum(len(findings) for findings in categories.values())
        print(f"{hostname}: {total_findings} findings")

if __name__ == "__main__":
    main()
