#!/bin/bash
echo "Installing Blackburn Marketplace..."
echo "Repository: https://github.com/pblacksnacks/the-blackburn-command-center"
echo ""
echo "Available plugins:"
python -c "import json; data=json.load(open('marketplace/plugins.json')); [print(f'  [{p[\"status\"]}] {p[\"name\"]}: {p[\"description\"]}') for p in data['plugins']]"
echo ""
echo "To activate a plugin, run: python cowork/gmail_scanner.py --help"
echo "Marketplace installed successfully."
