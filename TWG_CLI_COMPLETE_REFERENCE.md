# TWG CLI Complete Reference Documentation

**Binary Location:** `/Users/tchen7/.agents/skills/twg/scripts/twg`

---

## 1. twg --help

### Main Command Options

```
-V, --version                     output the version number
-e, --endpoint <url>              GraphQL Gateway endpoint URL (default: https://api.atlassian.com/graphql)
-u, --user <user>                 Atlassian account email for Basic auth
--token <token>                   API token or PAT for authentication
-s, --site <site>                 Atlassian site prefix (e.g. "mycompany") or cloud ID
-o, --output <format>             Output format: "text" (default) or "json"
--bbc-token <token>               Bitbucket Cloud API token (HTTP access token)
--api-version <version>           API contract version (current: v2)
--timeout-ms <ms>                 Per-request HTTP timeout in milliseconds
-h, --help                        display help for command
```

### Native Product Skills

- `jira` - Jira Software: agile project management, issue tracking, and software delivery
- `confluence` - Confluence: collaborative workspace for creating, sharing, and organizing team knowledge
- `jsm` - Jira Service Management: service desk platform
- `assets` - Assets: CMDB for tracking hardware, software, services, and company assets
- `goals [options]` - Atlassian Goals: search strategic goals by owner, org, health, status, and linked projects
- `projects [options]` - Atlassian Projects: search execution work by owner, org, role, status, and health
- `focus-areas [options]` - Focus: strategic planning tool
- `bitbucket|bb [options]` - Bitbucket: Git-based code management and CI/CD
- `csm` - Customer Service Management
- `jira-align` - Jira Align: connects enterprise strategy to team-level execution
- `talent` - Talent: workforce planning tool
- `teams [options]` - Teams: discover team identity, membership, and related metadata

### Relationship Skills

- `collaborators [options]` - Discover who collaborates most on the same work items
- `user [options] [account-id]` - Look up user details by Atlassian account ID
- `user-search|resolve [options]` - Find users by name and/or email

### Federated Skills

- `docs [options]` - Federated documents across Confluence + third-party providers
- `videos` - Federated videos surface
- `meetings [options]` - Federated meetings surface
- `spaces` - Federated spaces surface
- `pr [options] <ari>` - Show detailed information about a pull request

### Recipe Skills

- `recently-viewed [options]` - Show entities you have recently viewed
- `work` - Projection queries for cross-entity work activity
- `org-tree [options] [account-id]` - Show organizational hierarchy tree
- `focus-areas-tree [options] <ari>` - Show focus area hierarchy tree
- `context` - Projection queries for cross-entity context exploration

### Control-plane Skills

- `skills` - CLI skill installation and packaging utilities
- `integrations` - Integration control-plane commands
- `login [options]` - Configure CLI credentials
- `diagnostics` - Inspect local build metadata, auth resolution, and API connectivity

### Common Filters (across multiple commands)

- `--scope` - Supported by Atlassian Goals, Atlassian Projects, Focus, and work recipes
- `--role` - Supported by Atlassian Goals and Atlassian Projects
- `--updated-since`, `--created-since` - Supported by Atlassian Goals, Atlassian Projects, and Focus
- `--since` - Time windows supported by docs, meetings, collaborators, recently-viewed, and work
- `--first`, `--after` - Pagination supported on federated skills, collaborators, recently-viewed, and work

---

## 2. twg jira --help

### Usage

```
twg jira [options] [command]
```

### Options

```
-h, --help      display help for command
```

### Commands

- `board` - Jira board resources
- `dashboard` - Jira dashboard resources
- `field` - Jira field resources
- `space` - Jira space resources
- `sprint` - Jira sprint resources
- `workitem` - Jira work item resources
- `filter` - Reserved Jira filter namespace for ACLI-aligned filter commands
- `help [command]` - display help for command

### Examples

```
$ twg jira workitem get --id PROJ-123
$ twg jira workitem create --space PROJ --type Task --summary "New task" --assignee me
$ twg jira workitem update --id PROJ-123 --summary "Updated title" --assignee me
$ twg jira sprint start --board-id <board-id> --id <id> --name "Sprint 42" --start-date 2026-03-01 --end-date 2026-03-14
$ twg jira board get --id <board-id>
$ twg jira dashboard get <dashboard-id>
```

---

## 3. twg jira workitem --help

### Usage

```
twg jira workitem [options] [command]
```

### Options

```
-h, --help             display help for command
```

### Commands

- `update [options]` - Update fields on a Jira work item
- `comment` - Jira work item comment resources
- `link` - Jira work item link resources
- `issue-link` - Jira issue-to-issue link resources
- `watcher` - Jira work item watcher resources
- `statuses` - List available statuses
- `types` - List available issue types
- `get [options]` - Get Jira work items by ID or ARI
- `priorities` - List available priorities
- `archive [options]` - Archive Jira work items by IDs or asynchronously by JQL
- `create-bulk [options]` - Bulk create Jira work items from JSON payloads
- `delete [options] <id>` - Delete a Jira workitem by ID or ARI
- `unarchive [options]` - Unarchive Jira work items by ID or ARI
- `search [options]` - Search Jira work items by JQL
- `create [options]` - Create a Jira work item
- `transition [options]` - Transition a Jira work item to a new status
- `clone [options]` - Clone a Jira work item
- `help [command]` - display help for command

### Issue Key Resolution

All workitem commands accept issue keys (e.g. PROJ-123) wherever an issue ID or ARI is expected. Keys are automatically resolved to ARIs.

### Examples

```
$ twg jira workitem get --id PROJ-123
$ twg jira workitem search --jql "project = PROJ AND status = Open"
$ twg jira workitem create --space PROJ --type Task --summary "New task" --assignee me
$ twg jira workitem update --id PROJ-123 --summary "Updated title" --assignee me
$ twg jira workitem transition --id PROJ-123 --transition-id 21
$ twg jira workitem clone --issue-id PROJ-123
$ twg jira workitem delete PROJ-123
```

---

## 4. twg jira workitem get --help

### Usage

```
twg jira workitem get [options]
```

### Options

```
--variables-json <json>  Inline JSON object containing GraphQL variables for this command
--variables-file <path>  Path to a JSON file containing GraphQL variables for this command
--id <id>                Entity ID or ARI. Repeat to pass multiple values: --id "<id>" --id "<id>". (default: [])
-h, --help               display help for command
```

---

## 5. twg jira workitem create --help

### Usage

```
twg jira workitem create [options]
```

### Options

```
--variables-json <json>      Inline JSON object containing GraphQL variables for this command
--variables-file <path>      Path to a JSON file containing GraphQL variables for this command
--space <space>              Jira space (project) ID or ARI
--type <type>                Issue type name (e.g. "Task", "Bug") or ARI
--summary <summary>          Issue summary text
--description <description>  Issue description text (auto-wrapped to ADF)
--assignee <assignee>        Assignee account ID
-h, --help                   display help for command
```

---

## 6. twg jira workitem update --help

### Usage

```
twg jira workitem update [options]
```

### Options

```
--id <id>                    Issue key (e.g. PROJ-123) or issue ARI
--summary <summary>          New summary text
--description <description>  New description text (auto-wrapped to ADF)
--assignee <assignee>        Assignee: "me" for yourself, or a user ARI / account ID
--priority <priority>        Priority ARI or ID
--labels <labels>            Comma-separated list of labels (replaces existing)
-s, --site <site>            Atlassian site prefix or cloud ID
-o, --output <format>        Output format: json or text (default: "text")
-h, --help                   display help for command
```

---

## 7. twg jira workitem link --help

### Usage

```
twg jira workitem link [options] [command]
```

### Options

```
-h, --help             display help for command
```

### Commands

- `candidates` - Jira work item link candidate resources
- `types` - Jira issue link type resources
- `create [options]` - Link a Jira workitem to a project
- `delete [options] <id>` - Remove a Jira workitem link from a project
- `help [command]` - display help for command

### Navigate Deeper

```
$ twg jira workitem link create --help
$ twg jira workitem link delete --help
$ twg jira workitem link candidates search --help
$ twg jira workitem link types query --help
```

---

## 8. twg jira board --help

### Usage

```
twg jira board [options] [command]
```

### Options

```
-h, --help        display help for command
```

### Commands

- `backlog` - Jira board backlog resources
- `scope` - Jira board scope resources
- `backlog-view` - View backlog
- `cells` - Board cells
- `get [options]` - Get Jira boards by ID or ARI
- `view-settings` - Board view settings
- `search [options]` - Search Jira software boards for a project
- `help [command]` - display help for command

### Navigate Deeper

```
$ twg jira board get --help
$ twg jira board backlog --help
$ twg jira board scope --help
```

---

## 9. twg jira sprint --help

### Usage

```
twg jira sprint [options] [command]
```

### Options

```
-h, --help             display help for command
```

### Commands

- `complete [options]` - Complete a Jira sprint
- `create [options]` - Create a Jira sprint
- `delete [options] <id>` - Delete a Jira sprint
- `update [options]` - Update a Jira sprint
- `start [options]` - Start a Jira sprint
- `help [command]` - display help for command

### Examples

```
$ twg jira sprint create --board-id <board-id> --name "Sprint 42"
$ twg jira sprint start --board-id <board-id> --id <id> --start-date 2026-03-01 --end-date 2026-03-14
$ twg jira sprint complete --id <id>
```

---

## 10. twg goals --help

### Usage

```
twg goals [options] [command]
```

### Options

```
-s, --site <site>                         Atlassian site prefix or cloud ID (UUID)
-q, --tql <tql>                           TQL query string (default: "phase = in_progress OR phase = pending")
--status <status>                         Filter by status: all, on_track, off_track, at_risk, active, completed, cancelled, pending, paused
--scope <scope>                           Search scope: "all" (default), "me", "user", "org"
--role <role>                             Filter by role (with --scope me): owner, watcher
--account-id <id-or-ari>                  Org root user account ID or identity user ARI (requires --scope org)
--name <name>                             Resolve org root user by name (requires --scope org)
--email <email>                           Resolve org root user by email (requires --scope org)
-t, --tag <tag>                           Filter goals by tag name (case-insensitive, "#" prefix optional)
--updated-since <date>                    Only include goals updated on/after this date (YYYY-MM-DD or ISO datetime)
--created-since <date>                    Only include goals created on/after this date (YYYY-MM-DD or ISO datetime)
--include-contributing-projects           Include contributing Atlas projects for each returned goal
--include-parent-goal                     Include parent goal details for each returned goal
-n, --limit <number>                      Maximum number of goals to return (default: 100)
--sqlite-file <path>                      Write results to a SQLite DB file (table: goal_project_fact)
-h, --help                                display help for command
```

### Commands

- `link` - Link command
- `unlink` - Unlink command

### Status Values

**Health:** on_track, off_track, at_risk
**Lifecycle:** active (in progress), completed (done), cancelled, pending, paused

### Scope Values

- `all` - Search across the site (default)
- `me` - Only goals you own (or watch, with --role watcher)
- `user` - Goals for a specific user (requires --account-id)
- `org` - Goals owned by a root user and everyone in their reporting chain

### Role Values

- `owner` - Goals owned by the user (default)
- `watcher` - Goals watched/followed by the user

### TQL Query Examples

```
phase = in_progress OR phase = pending          Default goals (active + pending)
phase = in_progress                             Active goals (in progress)
phase = in_progress AND owner = currentUser()   Your active goals
phase = done                                    Completed goals
status = off_track                              Off track goals
name ~ "search term"                            Goals matching a name pattern
```

### Examples

```
$ twg goals                                 # All active + pending goals on site
$ twg goals --scope me                      # Your active + pending goals (owner)
$ twg goals --scope me --role watcher       # Goals you watch/follow
$ twg goals --scope user --account-id <id>  # Goals owned by a specific user
$ twg goals --scope user --account-id <id> --role watcher  # Goals watched by a user
$ twg goals --scope org                     # Your org's active + pending goals
$ twg goals --scope org --account-id 557058:abc...   # Specific root user's reporting chain
$ twg goals --status off_track              # All off-track goals
$ twg goals --status completed              # All completed goals
$ twg goals --scope me --status at_risk     # Your at-risk goals
$ twg goals -t rovo                         # All active + pending goals tagged "rovo"
$ twg goals --updated-since 2026-01-01      # Active + pending goals updated since Jan 1, 2026
$ twg goals --status all --created-since 2026-01-01   # All statuses, created since Jan 1, 2026
$ twg goals --status all --updated-since 2026-01-01   # All statuses, updated since Jan 1, 2026
$ twg goals --scope me -t "#platform"       # Your active + pending goals tagged "platform"
$ twg goals -q 'name ~ "adoption"'          # Search by name
$ twg goals --scope org --account-id 557058:abc... --include-parent-goal
$ twg goals --scope org --account-id 557058:abc... --include-contributing-projects
$ twg goals --scope org --account-id 557058:abc... --include-parent-goal --include-contributing-projects --sqlite-file ./goals-report.db
$ twg goals -o json                         # JSON envelope output
```

### Agent Mode Notes

For large org runs (especially with --include-parent-goal and --include-contributing-projects), prefer --sqlite-file <path> to avoid very large JSON payloads. The SQLite export uses one denormalized table: goal_project_fact.

---

## 11. twg projects --help

### Usage

```
twg projects [options] [command]
```

### Options

```
-s, --site <site>         Atlassian site prefix or cloud ID (UUID)
-q, --tql <tql>           TQL query string (default: "phase = in_progress")
--status <status>         Filter by status: all, on_track, off_track, at_risk, active, completed, pending, paused
--role <role>             Filter by role: owner (default), contributor, watcher
--scope <scope>           Search scope: "all" (default), "me", "user", "org"
--account-id <id-or-ari>  User account ID/identity user ARI for --scope user, or org root account ID(s) for --scope org (repeatable)
--name <name>             Resolve org root user by name (requires --scope org)
--email <email>           Resolve org root user by email (requires --scope org)
-t, --tag <tag>           Filter projects by tag name (case-insensitive, "#" prefix optional)
--updated-since <date>    Only include projects updated on/after this date (YYYY-MM-DD or ISO datetime)
--created-since <date>    Only include projects created on/after this date (YYYY-MM-DD or ISO datetime)
--since <date>            Deprecated alias for --updated-since
--include-linked-goals    Include active goals linked to each returned project
-n, --limit <number>      Maximum number of projects to return (default: 200)
-h, --help                display help for command
```

### Commands

- `get [options] <key>` - Get a single Atlassian project by exact project key

### Status Values

**Health:** on_track, off_track, at_risk
**Lifecycle:** active (in progress), completed (done), pending, paused

### Role Values

- `owner` - Projects you own (default)
- `contributor` - Projects you contribute to
- `watcher` - Projects you watch/follow

### Scope Values

- `all` - Search across the site (default)
- `me` - Only your projects (uses --role, default role=owner)
- `user` - Projects for a specific user (requires exactly one --account-id; uses --role)
- `org` - Projects for root user(s) and everyone in their reporting chains (uses --role)

### Examples

```
$ twg projects                                 # All active projects on site
$ twg projects --scope me                      # Your active projects (owner)
$ twg projects --scope me --role contributor   # Projects you contribute to
$ twg projects --scope me --role watcher       # Projects you watch
$ twg projects --scope user --account-id 557058:abc... --role watcher   # Projects a specific user watches
$ twg projects --scope org                     # Your org's active projects (owner)
$ twg projects --scope org --role watcher --account-id 557058:abc...   # Watched projects in a reporting chain
$ twg projects --scope org --role contributor --name "Jane Doe"   # Reporting chain from a named root user
$ twg projects --scope org --account-id 557058:abc... --account-id 557058:def...   # Multiple root users
$ twg projects --status off_track              # All off-track projects
$ twg projects --status completed              # All completed projects
$ twg projects --scope me --status at_risk     # Your at-risk projects
$ twg projects -t rovo                         # All active projects tagged "rovo"
$ twg projects --updated-since 2026-01-01      # Active projects updated since Jan 1, 2026
$ twg projects --status all --created-since 2026-01-01   # All statuses, created since Jan 1, 2026
$ twg projects --status all --updated-since 2026-01-01   # All statuses, updated since Jan 1, 2026
$ twg projects --scope me -t "#platform"       # Your active projects tagged "platform"
$ twg projects -q 'name ~ "platform"'         # Search by name
$ twg projects --include-linked-goals          # Include active linked goals
$ twg projects get ATLAS-119790                # Get a single project by exact key
$ twg projects get ATLAS-119790 --include-linked-goals
$ twg projects -o json                         # Machine-readable JSON
$ twg projects --scope me -o json              # JSON envelope output
```

---

## 12. twg work --help

### Usage

```
twg work [options] [command]
```

### Options

```
-h, --help       display help for command
```

### Commands

- `query [options]` - Query user-scoped work projection
- `help [command]` - display help for command

---

## 13. twg context --help

### Usage

```
twg context [options] [command]
```

### Options

```
-h, --help      display help for command
```

### Commands

- `jira` - Jira context projections
- `help [command]` - display help for command

---

## Summary of Output Format Options

All commands support:
- `-o, --output <format>` with values: `text` (human-readable, default) or `json` (machine-readable)

## Summary of Global Options Available

Common options across all commands:
- `-e, --endpoint <url>` - GraphQL Gateway endpoint
- `-u, --user <user>` - Atlassian account email
- `--token <token>` - API token or PAT
- `-s, --site <site>` - Atlassian site prefix or cloud ID
- `-o, --output <format>` - Output format (text or json)
- `--api-version <version>` - API contract version (current: v2)
- `--timeout-ms <ms>` - HTTP timeout in milliseconds
- `-h, --help` - Display help for command

## Summary of Common Pagination Parameters

- `--first <number>` - Limit number of results
- `--after <cursor>` - Pagination cursor for next page

## Summary of Common Filter Parameters

- `--scope <scope>` - Filter by scope (all, me, user, org)
- `--role <role>` - Filter by user role
- `--status <status>` - Filter by status
- `--updated-since <date>` - Filter by update date
- `--created-since <date>` - Filter by creation date
- `--since <date>` - Time window filter
- `--tag <tag>` - Filter by tags
- `-t, --tag <tag>` - Short form of tag filter
- `-q, --tql <tql>` - TQL query string
- `--jql <jql>` - JQL query string (for Jira searches)
