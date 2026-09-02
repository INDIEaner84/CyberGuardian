"""CyberGuardian Pro - Core Modules.

The browser control plane is dependency-free and must be able to start on a
fresh machine.  Optional desktop/security modules are therefore imported
lazily instead of at package import time.
"""

from importlib import import_module


_MODULES = {
    "NetworkScanner": ".network_scanner",
    "WifiAuditor": ".wifi_auditor",
    "PortManager": ".port_manager",
    "ProcessMonitor": ".process_monitor",
    "WireGuardManager": ".wireguard_manager",
    "Anonymizer": ".anonymizer",
    "RouterTools": ".router_tools",
    "IntrusionDetection": ".intrusion_detection",
    "FileIntegrityMonitor": ".file_integrity",
    "ForensicsTools": ".forensics",
    "DefenseOps": ".defense_ops",
    "ToolCatalog": ".tool_catalog",
}

__all__ = list(_MODULES)


def __getattr__(name):
    """Load a legacy desktop module only when a caller actually requests it."""

    module_name = _MODULES.get(name)
    if not module_name:
        raise AttributeError(name)
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
