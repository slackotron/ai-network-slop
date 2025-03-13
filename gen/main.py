# main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

# Create FastAPI app
app = FastAPI(
    title="Arista Network Config Generator",
    description="Generate Arista EOS configurations for various network scenarios",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Models for each configuration type
class AccessPortConfig(BaseModel):
    interface: str
    vlan: int
    description: Optional[str] = None
    spanning_tree: bool = True
    
class TrunkPortConfig(BaseModel):
    interface: str
    native_vlan: int
    allowed_vlans: List[int]
    description: Optional[str] = None
    
class ManagementConfig(BaseModel):
    hostname: str
    management_ip: str
    management_mask: str = "255.255.255.0"
    default_gateway: str
    dns_servers: List[str] = []
    ntp_servers: List[str] = []
    
class BGPConfig(BaseModel):
    asn: int
    router_id: str
    neighbors: List[dict]
    networks: List[str] = []
    
# Create template files
with open("templates/access_port.j2", "w") as f:
    f.write("""! Access Port Configuration for {{ interface }}
interface {{ interface }}
   description {{ description or "Access Port" }}
   switchport mode access
   switchport access vlan {{ vlan }}
   {% if spanning_tree %}
   spanning-tree portfast
   spanning-tree bpduguard enable
   {% endif %}
   no shutdown
""")

with open("templates/trunk_port.j2", "w") as f:
    f.write("""! Trunk Port Configuration for {{ interface }}
interface {{ interface }}
   description {{ description or "Trunk Port" }}
   switchport mode trunk
   switchport trunk native vlan {{ native_vlan }}
   switchport trunk allowed vlan {{ allowed_vlans|join(',') }}
   no shutdown
""")

with open("templates/management.j2", "w") as f:
    f.write("""! Management Configuration
hostname {{ hostname }}
!
interface Management1
   ip address {{ management_ip }}/{{ management_mask }}
   no shutdown
!
ip route 0.0.0.0/0 {{ default_gateway }}
!
{% if dns_servers %}
ip name-server {% for server in dns_servers %}{{ server }} {% endfor %}
{% endif %}
!
{% if ntp_servers %}
{% for server in ntp_servers %}
ntp server {{ server }}
{% endfor %}
{% endif %}
""")

with open("templates/bgp.j2", "w") as f:
    f.write("""! BGP Configuration
router bgp {{ asn }}
   router-id {{ router_id }}
   {% for neighbor in neighbors %}
   neighbor {{ neighbor.ip }} remote-as {{ neighbor.remote_asn }}
   {% if neighbor.get('description') %}
   neighbor {{ neighbor.ip }} description {{ neighbor.description }}
   {% endif %}
   {% if neighbor.get('update_source') %}
   neighbor {{ neighbor.ip }} update-source {{ neighbor.update_source }}
   {% endif %}
   {% endfor %}
   !
   {% for network in networks %}
   network {{ network }}
   {% endfor %}
""")

# API endpoints
@app.post("/generate/access-port", response_class=PlainTextResponse, tags=["Configuration Generators"])
async def generate_access_port(config: AccessPortConfig):
    """
    Generate Arista EOS configuration for an access port
    """
    return templates.get_template("access_port.j2").render(config.dict())

@app.post("/generate/trunk-port", response_class=PlainTextResponse, tags=["Configuration Generators"])
async def generate_trunk_port(config: TrunkPortConfig):
    """
    Generate Arista EOS configuration for a trunk port
    """
    return templates.get_template("trunk_port.j2").render(config.dict())

@app.post("/generate/management", response_class=PlainTextResponse, tags=["Configuration Generators"])
async def generate_management(config: ManagementConfig):
    """
    Generate Arista EOS management configuration
    """
    return templates.get_template("management.j2").render(config.dict())

@app.post("/generate/bgp", response_class=PlainTextResponse, tags=["Configuration Generators"])
async def generate_bgp(config: BGPConfig):
    """
    Generate Arista EOS BGP configuration
    """
    return templates.get_template("bgp.j2").render(config.dict())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
