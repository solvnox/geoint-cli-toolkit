from typing import Dict, List, Optional

import dns.resolver
from app.core.logger import log


def lookup_dns(domain: str) -> Dict[str, List[str]]:
    out = {}
    for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]:
        try:
            ans = dns.resolver.resolve(domain, rtype)
            out[rtype] = []
            for r in ans:
                if rtype == "MX":
                    out[rtype].append(f"{r.preference} {r.exchange}")
                else:
                    out[rtype].append(str(r))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.DNSException) as e:
            log.debug("DNS %s for %s: %s", rtype, domain, e)
    return out
