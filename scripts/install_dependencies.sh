#!/bin/bash

# Installation script for universal IFEval-FC inference system

echo "Installing universal IFEval-FC inference dependencies..."

# Clean up any unwanted files that might have been created by previous runs
echo "Cleaning up any unwanted files..."
rm -f "=0.0.20" "=0.1.0" "=1.0.0" "=3.8" "=4.0.0" ">=0.1.0" ">=1.0.0" ">=3.8" ">=4.0.0" ">=0.0.20" 2>/dev/null || true

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed or not in PATH"
    exit 1
fi

# Install all dependencies from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip3 install -r requirements.txt

# Download NLTK data (required for some checkers)
echo "Downloading NLTK data..."
python3 -c "
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    print('Downloaded NLTK punkt tokenizer')
"

# Colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${BLUE}${CYAN}"
echo """
                                ████                                                 █████               
                               ░░███                                                ░░███                
       █████ ███ █████  ██████  ░███   ██████   ██████  █████████████    ██████     ███████    ██████    
      ░░███ ░███░░███  ███░░███ ░███  ███░░███ ███░░███░░███░░███░░███  ███░░███   ░░░███░    ███░░███   
       ░███ ░███ ░███ ░███████  ░███ ░███ ░░░ ░███ ░███ ░███ ░███ ░███ ░███████      ░███    ░███ ░███   
       ░░███████████  ░███░░░   ░███ ░███  ███░███ ░███ ░███ ░███ ░███ ░███░░░       ░███ ███░███ ░███   
        ░░████░████   ░░██████  █████░░██████ ░░██████  █████░███ █████░░██████      ░░█████ ░░██████    
         ░░░░ ░░░░     ░░░░░░  ░░░░░  ░░░░░░   ░░░░░░  ░░░░░ ░░░ ░░░░░  ░░░░░░        ░░░░░   ░░░░░░     
                                                                                                         
                                                                                                         
                                                                                                         
 █████ ███████████ ██████████ █████   █████   █████████   █████                  ███████████   █████████ 
░░███ ░░███░░░░░░█░░███░░░░░█░░███   ░░███   ███░░░░░███ ░░███                  ░░███░░░░░░█  ███░░░░░███
 ░███  ░███   █ ░  ░███  █ ░  ░███    ░███  ░███    ░███  ░███                   ░███   █ ░  ███     ░░░ 
 ░███  ░███████    ░██████    ░███    ░███  ░███████████  ░███        ██████████ ░███████   ░███         
 ░███  ░███░░░█    ░███░░█    ░░███   ███   ░███░░░░░███  ░███       ░░░░░░░░░░  ░███░░░█   ░███         
 ░███  ░███  ░     ░███ ░   █  ░░░█████░    ░███    ░███  ░███      █            ░███  ░    ░░███     ███
 █████ █████       ██████████    ░░███      █████   █████ ███████████            █████       ░░█████████ 
░░░░░ ░░░░░       ░░░░░░░░░░      ░░░      ░░░░░   ░░░░░ ░░░░░░░░░░░            ░░░░░         ░░░░░░░░░  
                                                                                                         
"""
echo -e "${RESET}"

echo -e "${GREEN}${BOLD}Installation complete!${RESET}"
echo ""
echo -e "${CYAN}${BOLD}Next steps:${RESET}"
echo -e "${MAGENTA}1.${RESET} Copy env.example to .env:\n\n      cp env.example .env\n${RESET}"
echo -e "${MAGENTA}2.${RESET} Edit .env file and add your API keys"
echo -e "${MAGENTA}3.${RESET} Run evaluation: \n\n      python3 evaluate.py --provider <PROVIDER>${RESET}\n"
echo -e "${MAGENTA}4.${RESET} See metrics of the previous runs: \n\n      python3 scripts/view_results.py"
echo ""
echo -e "${YELLOW}Supported providers:${RESET} ${BOLD}'openai', 'anthropic', 'google', 'gigachat'${RESET}\n\n"
