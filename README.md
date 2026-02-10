# ignition-cli

CLI tool for the Ignition SCADA 8.3+ REST API.

## Quick Start

```bash
# Configure a gateway connection
ignition-cli config add dev --url https://gateway:8043 --token "keyId:secretKey"

# Check gateway status
ignition-cli gateway status

# Raw API access
ignition-cli api get /status
```

## Commands

- `ignition-cli config` — Manage gateway profiles
- `ignition-cli gateway` — Gateway status, backups, modules, logs
- `ignition-cli api` — Raw API access and endpoint discovery

Run `ignition-cli --help` for full usage information.

## License

MIT
