# Ashh66 66-Tool report

- Operator: Ashh66
- Product: 66-Tool
- Notice: public data only
- Updated: 2026-08-29T20:39:48Z
- Runs: 10

## 1. dns — example.com

- Source: DNS/UDP 1.1.1.1 (public resolver)
- Time: 2026-08-29T20:39:42Z
- Notice: public data only
- OK: True

```json
{
  "status": "NOERROR",
  "records": {
    "A": [
      "104.20.23.154",
      "172.66.147.243"
    ],
    "AAAA": [
      "2606:4700:10::6814:179a",
      "2606:4700:10::ac42:93f3"
    ],
    "MX": [
      "0 ."
    ],
    "NS": [
      "hera.ns.cloudflare.com",
      "elliott.ns.cloudflare.com"
    ],
    "TXT": [
      "v=spf1 -all",
      "_k2n1y4vw3qtb4skdx9e7dxt97qrmmq9"
    ],
    "CNAME": []
  }
}
```

## 2. username — ashh66

- Source: public profile URLs (operator-supplied handle)
- Time: 2026-08-29T20:39:44Z
- Notice: public data only
- OK: True

```json
{
  "handle": "ashh66",
  "checked": 19,
  "http_200": 7,
  "note": "HTTP 200 means the public URL returned 200, not a confirmed account.",
  "profiles": [
    {
      "url": "https://bitbucket.org/ashh66",
      "final_url": "https://bitbucket.org/ashh66/",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Bitbucket"
    },
    {
      "url": "https://codeberg.org/ashh66",
      "final_url": "https://codeberg.org/ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Codeberg"
    },
    {
      "url": "https://dev.to/ashh66",
      "final_url": "https://dev.to/ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Dev.to"
    },
    {
      "url": "https://hub.docker.com/u/ashh66",
      "final_url": "https://hub.docker.com/u/ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Docker Hub"
    },
    {
      "url": "https://github.com/ashh66",
      "final_url": "https://github.com/ashh66",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "GitHub"
    },
    {
      "url": "https://gitlab.com/ashh66",
      "final_url": "https://gitlab.com/users/sign_in",
      "status": 403,
      "ok_http": false,
      "error": null,
      "site": "GitLab"
    },
    {
      "url": "https://news.ycombinator.com/user?id=ashh66",
      "final_url": "https://news.ycombinator.com/user?id=ashh66",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "Hacker News"
    },
    {
      "url": "https://hackerone.com/ashh66",
      "final_url": "https://hackerone.com/ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "HackerOne"
    },
    {
      "url": "https://archive.org/details/@ashh66",
      "final_url": "https://archive.org/details/@ashh66",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "Internet Archive"
    },
    {
      "url": "https://keybase.io/ashh66",
      "final_url": "https://keybase.io/ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Keybase"
    },
    {
      "url": "https://linktr.ee/ashh66",
      "final_url": "https://linktr.ee/ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Linktree"
    },
    {
      "url": "https://medium.com/@ashh66",
      "final_url": "https://medium.com/@ashh66",
      "status": 403,
      "ok_http": false,
      "error": null,
      "site": "Medium"
    },
    {
      "url": "https://www.npmjs.com/~ashh66",
      "final_url": "https://www.npmjs.com/~ashh66",
      "status": 403,
      "ok_http": false,
      "error": null,
      "site": "npm"
    },
    {
      "url": "https://pypi.org/user/ashh66/",
      "final_url": "https://pypi.org/user/ashh66/",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "PyPI"
    },
    {
      "url": "https://www.reddit.com/user/ashh66",
      "final_url": "https://www.reddit.com/user/ashh66/",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "Reddit"
    },
    {
      "url": "https://sr.ht/~ashh66",
      "final_url": "https://sr.ht/~ashh66/",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "SourceHut"
    },
    {
      "url": "https://www.twitch.tv/ashh66",
      "final_url": "https://www.twitch.tv/ashh66",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "Twitch"
    },
    {
      "url": "https://en.wikipedia.org/wiki/User:ashh66",
      "final_url": "https://en.wikipedia.org/wiki/User:Ashh66",
      "status": 404,
      "ok_http": false,
      "error": null,
      "site": "Wikipedia"
    },
    {
      "url": "https://www.youtube.com/@ashh66",
      "final_url": "https://www.youtube.com/@ashh66?cbrd=1&ucbcb=1",
      "status": 200,
      "ok_http": true,
      "error": null,
      "site": "YouTube"
    }
  ]
}
```

## 3. email — lab@example.com

- Source: local syntax check + public Gravatar URLs
- Time: 2026-08-29T20:39:44Z
- Notice: public data only
- OK: True

```json
{
  "email": "lab@example.com",
  "syntax_ok": true,
  "gravatar_md5": "02428a847ecf393cc0afe41856dc541b",
  "gravatar_urls": {
    "avatar": "https://www.gravatar.com/avatar/02428a847ecf393cc0afe41856dc541b?d=404",
    "profile_json": "https://www.gravatar.com/02428a847ecf393cc0afe41856dc541b.json"
  },
  "gravatar_image_present": false,
  "gravatar_error": null,
  "breach_lookup_pages": [
    "https://haveibeenpwned.com/",
    "https://monitor.mozilla.org/"
  ],
  "note": "66-Tool does not query breach databases. Open a lookup page and paste the address yourself if you are allowed to."
}
```

## 4. headers — https://example.com

- Source: public HTTP(S) response headers
- Time: 2026-08-29T20:39:44Z
- Notice: public data only
- OK: False
- Error: [Errno 11001] getaddrinfo failed

```json
{}
```

## 5. cert — example.com:443

- Source: TLS certificate presented by example.com:443
- Time: 2026-08-29T20:39:45Z
- Notice: public data only
- OK: True

```json
{
  "host": "example.com",
  "port": 443,
  "protocol": "TLSv1.3",
  "subject": {
    "commonName": "example.com"
  },
  "issuer": {
    "countryName": "US",
    "organizationName": "SSL Corporation",
    "commonName": "Cloudflare TLS Issuing ECC CA 3"
  },
  "not_before": "Jul 29 22:10:08 2026 GMT",
  "not_after": "Oct 27 22:17:21 2026 GMT",
  "not_before_iso": "2026-07-29T22:10:08Z",
  "not_after_iso": "2026-10-27T22:17:21Z",
  "serial": "0624D0AB311558780B7D5213B9631831",
  "sans": [
    "example.com",
    "*.example.com"
  ]
}
```

## 6. whois — example.com

- Source: WHOIS port 43 (whois.iana.org -> whois.verisign-grs.com)
- Time: 2026-08-29T20:39:45Z
- Notice: public data only
- OK: True

```json
{
  "servers": "whois.iana.org -> whois.verisign-grs.com",
  "extracted": {
    "registrar": "RESERVED-Internet Assigned Numbers Authority",
    "created": "1995-08-14T04:00:00Z",
    "updated": "2026-08-14T08:01:43Z",
    "expires": "2027-08-13T04:00:00Z"
  },
  "name_servers": [
    "ELLIOTT.NS.CLOUDFLARE.COM",
    "HERA.NS.CLOUDFLARE.COM"
  ],
  "record": "Domain Name: EXAMPLE.COM\r\n   Registry Domain ID: 2336799_DOMAIN_COM-VRSN\r\n   Registrar WHOIS Server: whois.iana.org\r\n   Registrar URL: http://res-dom.iana.org\r\n   Updated Date: 2026-08-14T08:01:43Z\r\n   Creation Date: 1995-08-14T04:00:00Z\r\n   Registry Expiry Date: 2027-08-13T04:00:00Z\r\n   Registrar: RESERVED-Internet Assigned Numbers Authority\r\n   Registrar IANA ID: 376\r\n   Registrar Abuse Contact Email:\r\n   Registrar Abuse Contact Phone:\r\n   Domain Status: clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited\r\n   Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited\r\n   Domain Status: clientUpdateProhibited https://icann.org/epp#clientUpdateProhibited\r\n   Name Server: ELLIOTT.NS.CLOUDFLARE.COM\r\n   Name Server: HERA.NS.CLOUDFLARE.COM\r\n   DNSSEC: signedDelegation\r\n   DNSSEC DS Data: 2371 13 2 C988EC423E3880EB8DD8A46FE06CA230EE23F35B578D64E78B29C3E1C83D245A\r\n   URL of the ICANN Whois Inaccuracy Complaint Form: https://www.icann.org/wicf/\r\n>>> Last update of whois database: 2026-08-29T20:39:28Z <<<\r\n\r\nFor more information on Whois status codes, please visit https://icann.org/epp\r\n\r\nNOTICE: The expiration date displayed in this record is the date the\r\nregistrar's sponsorship of the domain name registration in the registry is\r\ncurrently set to expire. This date does not necessarily reflect the expiration\r\ndate of the domain name registrant's agreement with the sponsoring\r\nregistrar.  Users may consult the sponsoring registrar's Whois database to\r\nview the registrar's reported date of expiration for this registration.\r\n\r\nTERMS OF USE: You are not authorized to access or query our Whois\r\ndatabase through the use of electronic processes that are high-volume and\r\nautomated except as reasonably necessary to register domain names or\r\nmodify existing registrations; the Data in VeriSign Global Registry\r\nServices' (\"VeriSign\") Whois database is provided by VeriSign for\r\ninformation purposes only, and to assist persons in obtaining information\r\nabout or related to a domain name registration record. VeriSign does not\r\nguarantee its accuracy. By submitting a Whois query, you agree to abide\r\nby the following terms of use: You agree that you may use this Data only\r\nfor lawful purposes and that under no circumstances will you use this Data\r\nto: (1) allow, enable, or otherwise support the transmission of mass\r\nunsolicited, commercial advertising or solicitations via e-mail, telephone,\r\nor facsimile; or (2) enable high volume, automated, electronic processes\r\nthat apply to VeriSign (or its computer systems). The compilation,\r\nrepackaging, dissemination or other use of this Data is expressly\r\nprohibited without the prior written consent of VeriSign. You agree not to\r\nuse electronic processes that are automated and high-volume to access or\r\nquery the Whois database except as reasonably necessary to register\r\ndomain names or modify existing registrations. VeriSign reserves the right\r\nto restrict your access to the Whois database in its sole discretion to ensure\r\noperational stability.  VeriSign may restrict or terminate your access to the\r\nWhois database for failure to abide by these terms of use. VeriSign\r\nreserves the right to modify these terms at any time.\r\n\r\nThe Registry database contains ONLY .COM, .NET, .EDU domains and\r\nRegistrars."
}
```

## 7. ip — 1.1.1.1

- Source: reverse DNS + RDAP (rdap.org)
- Time: 2026-08-29T20:39:46Z
- Notice: public data only
- OK: True

```json
{
  "ip": "1.1.1.1",
  "queried": "1.1.1.1",
  "reverse_dns": "one.one.one.one",
  "rdap": {
    "handle": "1.1.1.0 - 1.1.1.255",
    "name": "APNIC-LABS",
    "type": "ASSIGNED PORTABLE",
    "country": "AU",
    "start_address": "1.1.1.0",
    "end_address": "1.1.1.255",
    "cidrs": [
      "1.1.1.0/24"
    ],
    "entities": [
      {
        "handle": "AIC3-AP",
        "roles": [
          "technical",
          "administrative"
        ],
        "name": "APNICRANDNET Infrastructure Contact"
      },
      {
        "handle": "IRT-APNICRANDNET-AU",
        "roles": [
          "abuse"
        ],
        "name": "IRT-APNICRANDNET-AU"
      },
      {
        "handle": "ORG-ARAD1-AP",
        "roles": [
          "registrant"
        ],
        "name": "APNIC Research and Development"
      }
    ],
    "rdap_url": "https://rdap.apnic.net/ip/1.1.1.0/24"
  },
  "rdap_error": null,
  "note": "No port scan. Use Port-Scanner on hosts you are allowed to test."
}
```

## 8. meta — README.md

- Source: local file metadata (operator-provided)
- Time: 2026-08-29T20:39:46Z
- Notice: public data only
- OK: True

```json
{
  "path": "E:\\Omen-Tool\\README.md",
  "size": 2730,
  "modified_utc": "2026-08-29T20:37:29Z",
  "sha256": "ab5e06a92c953db7389f73ead77e3961013788e2db62bc56502a303a92559910",
  "kind": "unknown",
  "magic_hex": "232036362d546f6f6c0d0a0d",
  "metadata": {}
}
```

## 9. wayback — https://example.com

- Source: Wayback Machine CDX API
- Time: 2026-08-29T20:39:47Z
- Notice: public data only
- OK: True

```json
{
  "query": "https://web.archive.org/cdx/search/cdx?url=https%3A%2F%2Fexample.com&output=json&limit=5&fl=timestamp,original,statuscode,mimetype,digest",
  "count": 5,
  "snapshots": [
    {
      "timestamp": "20020120142510",
      "original": "http://example.com:80/",
      "statuscode": "200",
      "mimetype": "text/html",
      "digest": "HT2DYGA5UKZCPBSFVCV3JOBXGW2G5UUA"
    },
    {
      "timestamp": "20020328012821",
      "original": "http://www.example.com:80/",
      "statuscode": "200",
      "mimetype": "text/html",
      "digest": "UY3I2DT2AMWAY6DECFCFYMT5ZOTFHUCH"
    },
    {
      "timestamp": "20020524041628",
      "original": "http://www.example.com:80/",
      "statuscode": "200",
      "mimetype": "text/html",
      "digest": "UY3I2DT2AMWAY6DECFCFYMT5ZOTFHUCH"
    },
    {
      "timestamp": "20020528114741",
      "original": "http://www.example.com:80/",
      "statuscode": "200",
      "mimetype": "text/html",
      "digest": "UY3I2DT2AMWAY6DECFCFYMT5ZOTFHUCH"
    },
    {
      "timestamp": "20020529173502",
      "original": "http://www.example.com:80/",
      "statuscode": "200",
      "mimetype": "text/html",
      "digest": "UY3I2DT2AMWAY6DECFCFYMT5ZOTFHUCH"
    }
  ]
}
```

## 10. subdomains — example.com

- Source: Certificate Transparency via Cert Spotter
- Time: 2026-08-29T20:39:48Z
- Notice: public data only
- OK: True

```json
{
  "query": "https://api.certspotter.com/v1/issuances?domain=example.com&include_subdomains=true&expand=dns_names",
  "names": [
    "example.com",
    "www.example.com"
  ],
  "count": 2,
  "available": 2,
  "note": "Names as published in public CT logs. 66-Tool does not probe these hosts."
}
```
