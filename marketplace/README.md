# Blackburn Marketplace

Plugin ecosystem for the Blackburn Command Center. Extend your sales intelligence pipeline with automation plugins that connect to external services, add new workflows, and keep your pipeline running on autopilot.

## Available Plugins

| Plugin | Status | Description |
|--------|--------|-------------|
| [Gmail Pipeline](gmail-pipeline/) | **Active** | Automated Gmail scanning via MCP — scores, researches, and briefs daily |
| Salesforce CRM Sync | Coming Soon | Two-way lead sync between Command Center and Salesforce |
| Slack Notifications | Coming Soon | Real-time alerts for A-grade leads and competitive threats |
| Calendar Integration | Coming Soon | Auto-schedule discovery calls based on lead priority |
| Competitive Intel Auto-Update | Coming Soon | Continuous monitoring of competitor moves and market shifts |

## How Plugins Work

Each plugin lives in its own directory under `marketplace/` and follows a standard structure:

```
marketplace/
├── plugins.json              # Central registry of all plugins
├── README.md                 # This file
└── gmail-pipeline/           # Plugin directory
    ├── manifest.json          # Plugin metadata and dependencies
    ├── INSTALL.md             # Installation instructions
    └── (references cowork/)   # Actual code lives in cowork/
```

Plugins integrate with the Command Center pipeline by:
1. Implementing an `EmailSource` (for inbound data) or consuming pipeline output (for outbound actions)
2. Using MCP servers for external service connections (Gmail, Slack, Salesforce, etc.)
3. Running on a schedule or on-demand via Cowork commands

## Installing a Plugin

### 1. Check the registry

Review `plugins.json` to find available plugins and their requirements.

### 2. Follow the plugin's INSTALL.md

Each plugin has its own installation guide. Generally:

```bash
# Ensure dependencies are met
pip install -r requirements.txt

# Configure environment variables
echo 'ANTHROPIC_API_KEY=your-key' >> .env

# Connect required MCP servers (plugin-specific)
# See the plugin's INSTALL.md for details

# Verify the plugin works
python cowork/gmail_scanner.py --help
```

### 3. Enable in Cowork

Tell Cowork to use the plugin's skill definition (e.g., `cowork/SKILL.md`) for automated scheduling.

## Coming Soon

### Salesforce CRM Sync
Bi-directional sync between the Command Center SQLite database and Salesforce. New leads scored in the pipeline auto-create Salesforce Leads with MEDDPICC fields mapped. Updates in Salesforce flow back to keep the local DB current.

### Slack Notifications
Real-time Slack alerts when:
- A new A-grade lead is detected
- A competitive bake-off is identified
- A lead's score trends upward across multiple emails
- The daily briefing is ready

### Calendar Integration
Automatically suggest or create calendar events for high-priority discovery calls. Integrates with Google Calendar MCP to find open slots and propose meeting times based on lead urgency.

### Competitive Intelligence Auto-Update
Scheduled web searches for tracked competitors (OpenAI, GitHub, etc.) that update competitive battle cards and alert when significant market moves are detected.

## Plugin Submission Template

Want to build a plugin for the Blackburn Marketplace? Follow this template:

### Required Files

1. **`manifest.json`** — Plugin metadata:
   ```json
   {
     "name": "your-plugin-name",
     "version": "0.1.0",
     "description": "What your plugin does",
     "author": "Your Name",
     "code_path": "../path-to-code/",
     "entry_point": "main_script.py",
     "dependencies": {
       "python": ["package1", "package2"],
       "mcp_servers": ["server-name"]
     },
     "env_vars": {
       "required": ["VAR_NAME"],
       "optional": ["OPTIONAL_VAR"]
     }
   }
   ```

2. **`INSTALL.md`** — Step-by-step installation guide

3. **Plugin code** — Either in the plugin directory or referenced from elsewhere in the repo

### Guidelines

- Plugins must not modify existing pipeline agents
- All external service access goes through MCP servers
- Include clear error messages when dependencies are missing
- Support both Anthropic and GitLab modes where applicable
- Document all environment variables
