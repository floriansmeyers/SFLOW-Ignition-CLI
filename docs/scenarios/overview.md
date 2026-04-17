# Use Case Coverage: SFLOW Ignition CLI vs. Real-World Needs

Research across the [Inductive Automation Forum](https://forum.inductiveautomation.com/),
CI/CD blog posts, the [design-group Tag CICD module](https://github.com/design-group/ignition-tag-cicd-module),
the [WhiskeyHouse Ignition MCP server](https://github.com/WhiskeyHouse/ignition-mcp), and
[Ignition 8.3 documentation](https://docs.inductiveautomation.com/docs/8.3/) identified
**17 day-to-day use cases** that automation engineers perform with the Ignition REST API.

The CLI covers all 17 as individual commands. However, many of the *workflow* scenarios
we originally documented are now better handled by Ignition 8.3 native features
(Git integration, EAM scheduling, OPC-UA auto-reconnect) or dedicated tooling
(Ansible, monitoring stacks). The 8 scenarios below focus on tasks where the CLI
provides genuine, hard-to-replicate value.

## API Use Cases Covered

| # | Use Case | Frequency | CLI Commands |
|---|----------|-----------|--------------|
| 1 | **CI/CD Pipeline Integration** — scan for project/config changes after Git push | Per-commit | `gateway scan-projects`, `gateway scan-config` |
| 2 | **Deployment Mode Management** — create/update/delete modes, assign resources per environment | Per-deployment | `mode list/show/create/update/delete/assign/unassign` |
| 3 | **Gateway Health Monitoring** — check status, version, edition, uptime | Continuous | `gateway status`, `gateway info` |
| 4 | **Module Health Checks** — verify healthy/quarantined modules | Daily | `gateway modules`, `gateway modules --quarantined` |
| 5 | **Gateway Backup & Restore** — automated backups, disaster recovery | Nightly | `gateway backup`, `gateway restore` |
| 6 | **Project CRUD** — create, list, show, delete projects | Per-deployment | `project list/show/create/delete` |
| 7 | **Project Migration** — export/import .zip between gateways | Per-deployment | `project export/import/copy/rename` |
| 8 | **Tag Export/Import** — version control, CI/CD tag deployment | Per-deployment | `tag export/import` with collision policies |
| 9 | **Tag Browsing** — explore tag tree, discover structure | On-demand | `tag browse`, `tag providers` |
| 10 | **Device Management** — list/inspect/restart OPC and device connections | Daily | `device list/show/restart` |
| 11 | **Resource CRUD** — database connections, alarm journals, API tokens, etc. | Per-provisioning | `resource list/show/create/update/delete/names/types` |
| 12 | **Binary Datafile Management** — upload/download files on resources | Per-deployment | `resource upload/download` |
| 13 | **Gateway Log Retrieval** — centralized logging, troubleshooting | Continuous | `gateway logs/log-download/loggers` |
| 14 | **Entity/OPC Browse** — discover devices, tags, data points | Commissioning | `gateway entity-browse` |
| 15 | **Raw API Escape Hatch** — any endpoint not covered by typed commands | On-demand | `api get/post/put/delete/discover/spec` |
| 16 | **Configuration Drift Detection** — compare gateways | On-demand | `project diff` (resource/tag/mode diff planned) |
| 17 | **Fleet Compliance Audit** — rule-driven audit across gateway fleet with Markdown report | Monthly/quarterly | `gateway info/status/modules/logs`, `project list`, `device list`, `tag providers`, `mode list` |

## Community Pain Points We Already Solve

The research uncovered major pain points reported on the
[Inductive Automation Forum](https://forum.inductiveautomation.com/) and in blog posts.
Our CLI already addresses every one of them:

| Pain Point | How the CLI Solves It |
|------------|----------------------|
| **Auth header confusion** — `X-Ignition-API-Token` is non-standard and poorly documented | Handled transparently via gateway profiles |
| **JSON array requirement** — resource create/update expects `[...]`, not a single object | CLI wraps automatically |
| **Signature fetch for update/delete** — extra round-trip to get the current signature | CLI auto-fetches before mutating |
| **`type` param required for tag export** — undocumented, causes confusing errors | Always included |
| **`collisionPolicy` required for tag import** — omitting it produces a 400 error | Exposed as `--collision-policy` with sensible default (`MergeOverwrite`) |
| **Non-UTF8 bytes in large tag exports** — breaks standard JSON parsing | Fallback decoding in the HTTP client |
| **Mode-scoped resource signatures differ** — using the base signature fails | CLI fetches the correct signature per collection |
| **No practical CLI tool existed** — engineers resorted to curl, Postman, or custom scripts | The CLI provides a complete, ergonomic interface |

## Sources

- [Innorobix: Deploying Ignition at Scale with Git and CI/CD](https://www.innorobix.com/deploying-ignition-projects-at-scale-with-git-and-ci-cd-tools/)
- [Ignition 8.3 Version Control Guide](https://docs.inductiveautomation.com/docs/8.3/tutorials/version-control-guide)
- [Hallam-ICS: New Features in Ignition 8.3](https://www.hallam-ics.com/blog/new-features-coming-in-ignition-8.3-a-comprehensive-look)
- [Forum: Git Deployment Best Practices](https://forum.inductiveautomation.com/t/ignition-8-3-git-deployment-best-practices/109355)
- [Forum: Understanding 8.3 Deployment Modes](https://forum.inductiveautomation.com/t/understanding-8-3-deployment-modes/110565)
- [Forum: Web API to Monitor Server Health](https://forum.inductiveautomation.com/t/web-api-to-monitor-ignition-server-health/46285)
- [Forum: Has Anyone Gotten the API to Work?](https://forum.inductiveautomation.com/t/has-anyone-gotten-the-api-to-work/109101)
- [Forum: API Keys](https://forum.inductiveautomation.com/t/ignition-api-keys/109660)
- [Forum: Best Practices for Multiple Gateways](https://forum.inductiveautomation.com/t/best-practices-for-management-of-multiple-ignition-gateways/18482)
- [Forum: Creating Tag Groups via API](https://forum.inductiveautomation.com/t/creating-tag-groups-with-the-openapi-endpoints-in-the-gateway/111633)
- [Forum: Multi-Developer Deployment](https://forum.inductiveautomation.com/t/best-practices-for-deployment-management-in-a-multi-developer-environment/100905)
- [GitHub: design-group/ignition-tag-cicd-module](https://github.com/design-group/ignition-tag-cicd-module)
- [GitHub: WhiskeyHouse/ignition-mcp](https://github.com/WhiskeyHouse/ignition-mcp)
- [Ignition Pro Tips Blog](https://inductiveautomation.com/blog/ignition-83-pro-tips-smarter-solution-management)
- [DMC: Dynamically Creating Tags in Ignition](https://www.dmcinfo.com/latest-thinking/blog/id/10345/dynamically-creating-stations-and-tags-in-ignition)

## Scenario Documentation

Ready-to-use scripts and workflows for tasks where the CLI provides unique value
that Ignition's native features and standard tooling don't cover:

| # | Scenario | Key Commands |
|---|----------|-------------|
| 1 | [Tag Snapshot & Version Control](01-tag-snapshot-version-control.md) | `tag export` |
| 2 | [Tag Diff Across Gateways](02-tag-diff-across-gateways.md) | `tag export` |
| 3 | [Resource Inventory Export](03-resource-inventory-export.md) | `resource list/types` |
| 4 | [Bulk Device Commissioning](04-bulk-device-commissioning.md) | `resource create`, `device list` |
| 5 | [Tag Template Factory](05-tag-template-factory.md) | `tag import/browse` |
| 6 | [Upgrade Verification](06-upgrade-verification.md) | `gateway info/modules`, `project list`, `device list`, `tag providers` |
| 7 | [Compliance Audit Report](07-compliance-report/README.md) | `gateway info/status/modules/logs`, `project list`, `device list`, `tag providers`, `mode list` |
| 8 | [Environment Cloning](08-environment-cloning.md) | `gateway backup/restore`, `resource show/update`, `mode create` |

## Removed Scenarios

The following scenarios were removed because they are better handled by Ignition 8.3
native features or dedicated infrastructure tooling:

| Old # | Scenario | Reason for Removal |
|-------|----------|--------------------|
| 1 | Nightly Backup Rotation | EAM handles this natively. Without EAM, it's a trivial cron + curl one-liner. |
| 2 | Dev-to-Prod Promotion | Obsoleted by Ignition 8.3's native Git integration. `git push` + `scan-projects` replaces export/import zips. |
| 4 | Gateway Health Dashboard | Monitoring belongs in Nagios/Zabbix/Datadog/PRTG. Ignition exposes JMX metrics. EAM has a status dashboard. |
| 5 | Device Connection Watchdog | OPC-UA drivers have built-in auto-reconnect. Blind restart loops mask real problems. |
| 6 | Fresh Gateway Provisioning | Backup/restore is simpler, faster, and atomic. Scenario 8 (Environment Cloning) covers remap-after-restore. |
| 8 | Pre-Deployment Validation | CI/CD systems have native gating. The bash implementation is fragile compared to Ansible or proper CI. |
| 10 | Multi-Gateway Project Sync | Largely obsoleted by 8.3 Git integration. EAM shows project deployment status across agents. |
| 11 | CI/CD Pipeline (GitHub/Azure) | With 8.3 Git integration, CI/CD is: push to main, scan-projects. No export/import zips needed. |
| 13 | Fleet Drift Detection | Config management at fleet scale belongs in Ansible/Terraform. Auto-remediation is a footgun for intentionally different configs. |
| 14 | Disaster Recovery Drill | Verification is shallow (name comparison only). Doesn't verify actual functionality. |

## Future Considerations

Two areas worth considering for future versions:

1. **`diff` for resources/tags/modes** between gateways — extends the existing `project diff` pattern
2. **Batch gateway operations** — e.g. `--gateways dev,staging,prod` flag or a `batch` command

Neither is critical today — the `api` escape hatch plus shell scripting covers both.
