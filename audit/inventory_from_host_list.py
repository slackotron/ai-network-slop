from nornir import InitNornir
from nornir.core.inventory import Host, Group, Inventory, Defaults
from typing import Dict, List
import yaml

class DynamicInventory:
    def __init__(self, 
                 hosts_file: str,
                 username: str,
                 password: str,
                 platform: str = 'eos',
                 port: int = 443):
        """
        Initialize dynamic inventory creator.
        
        Args:
            hosts_file: Path to text file containing hostnames/IPs
            username: Device username
            password: Device password
            platform: Device platform (default: eos)
            port: Device port (default: 443)
        """
        self.hosts_file = hosts_file
        self.username = username
        self.password = password
        self.platform = platform
        self.port = port

    def read_hosts(self) -> List[str]:
        """Read hosts from text file."""
        with open(self.hosts_file, 'r') as f:
            # Strip whitespace and empty lines
            return [line.strip() for line in f if line.strip()]

    def create_host_dict(self, hostname: str) -> Dict:
        """Create host dictionary for a single host."""
        return {
            hostname: {
                'hostname': hostname,
                'groups': ['network_devices'],
                'data': {
                    'platform': self.platform
                }
            }
        }

    def create_groups_dict(self) -> Dict:
        """Create groups dictionary with default settings."""
        return {
            'network_devices': {
                'username': self.username,
                'password': self.password,
                'platform': self.platform,
                'connection_options': {
                    'napalm': {
                        'extras': {
                            'optional_args': {
                                'transport': 'https',
                                'port': self.port
                            }
                        }
                    }
                }
            }
        }

    def create_defaults_dict(self) -> Dict:
        """Create defaults dictionary."""
        return {
            'username': self.username,
            'password': self.password,
            'platform': self.platform
        }

    def create_inventory_files(self, output_dir: str = '.') -> None:
        """
        Create Nornir inventory files from hosts list.
        
        Args:
            output_dir: Directory to write inventory files
        """
        # Read hosts from file
        hosts = self.read_hosts()
        
        # Create inventory dictionaries
        hosts_dict = {}
        for host in hosts:
            hosts_dict.update(self.create_host_dict(host))
            
        groups_dict = self.create_groups_dict()
        defaults_dict = self.create_defaults_dict()
        
        # Write inventory files
        with open(f'{output_dir}/hosts.yaml', 'w') as f:
            yaml.dump(hosts_dict, f)
            
        with open(f'{output_dir}/groups.yaml', 'w') as f:
            yaml.dump(groups_dict, f)
            
        with open(f'{output_dir}/defaults.yaml', 'w') as f:
            yaml.dump(defaults_dict, f)
            
        # Create main config file
        config_dict = {
            'inventory': {
                'plugin': 'SimpleInventory',
                'options': {
                    'host_file': 'hosts.yaml',
                    'group_file': 'groups.yaml',
                    'defaults_file': 'defaults.yaml'
                }
            },
            'runner': {
                'plugin': 'threaded',
                'options': {
                    'num_workers': 10
                }
            }
        }
        
        with open(f'{output_dir}/config.yaml', 'w') as f:
            yaml.dump(config_dict, f)

    def create_nornir(self) -> Inventory:
        """
        Create Nornir inventory object directly from hosts list.
        
        Returns:
            Nornir inventory object
        """
        # Read hosts
        hosts = self.read_hosts()
        
        # Create inventory objects
        hosts_dict = {}
        for hostname in hosts:
            hosts_dict[hostname] = Host(
                name=hostname,
                hostname=hostname,
                groups=['network_devices'],
                platform=self.platform,
                username=self.username,
                password=self.password
            )
            
        groups_dict = {
            'network_devices': Group(
                name='network_devices',
                connection_options={
                    'napalm': {
                        'extras': {
                            'optional_args': {
                                'transport': 'https',
                                'port': self.port
                            }
                        }
                    }
                }
            )
        }
        
        defaults = Defaults(
            username=self.username,
            password=self.password,
            platform=self.platform
        )
        
        return Inventory(
            hosts=hosts_dict,
            groups=groups_dict,
            defaults=defaults
        )

def main():
    """Example usage of dynamic inventory creation."""
    # Example hosts.txt file content:
    # 192.168.1.10
    # 192.168.1.11
    # switch1.example.com
    # switch2.example.com
    
    # Create inventory manager
    inventory = DynamicInventory(
        hosts_file='hosts.txt',
        username='admin',
        password='your_password',
        platform='eos',
        port=443
    )
    
    # Method 1: Create inventory files
    print("Creating inventory files...")
    inventory.create_inventory_files()
    
    # Initialize Nornir from files
    nr = InitNornir(config_file="config.yaml")
    
    # Method 2: Create Nornir inventory directly
    print("\nCreating Nornir inventory directly...")
    inv = inventory.create_nornir()
    nr = InitNornir(inventory=inv)
    
    # Print inventory
    print("\nInventory hosts:")
    for host in nr.inventory.hosts:
        print(f"- {host}")

if __name__ == "__main__":
    main()
