#!/bin/bash
# Deploy Signal as systemd service
# Usage: sudo ./scripts/deploy_systemd.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Signal Systemd Deployment Script${NC}"
echo "========================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (sudo)${NC}"
   exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing uv package manager...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create signal user if doesn't exist
if ! id -u signal &> /dev/null; then
    echo -e "${YELLOW}Creating signal user...${NC}"
    useradd --system --shell /bin/bash --home-dir /opt/signal signal
fi

# Create deployment directory
DEPLOY_DIR="/opt/signal"
echo -e "${YELLOW}Setting up deployment directory: $DEPLOY_DIR${NC}"
mkdir -p $DEPLOY_DIR
mkdir -p $DEPLOY_DIR/logs

# Copy project files
echo -e "${YELLOW}Copying project files...${NC}"
cp -r src $DEPLOY_DIR/
cp pyproject.toml $DEPLOY_DIR/
cp uv.lock $DEPLOY_DIR/
cp config.example.yaml $DEPLOY_DIR/

# Check if config.yaml exists
if [[ ! -f $DEPLOY_DIR/config.yaml ]]; then
    echo -e "${YELLOW}Creating config.yaml from template...${NC}"
    cp $DEPLOY_DIR/config.example.yaml $DEPLOY_DIR/config.yaml
    echo -e "${RED}IMPORTANT: Edit $DEPLOY_DIR/config.yaml with your settings!${NC}"
fi

# Set ownership
chown -R signal:signal $DEPLOY_DIR

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
cd $DEPLOY_DIR
sudo -u signal uv sync

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
cp scripts/signal.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start service
echo -e "${YELLOW}Enabling and starting service...${NC}"
systemctl enable signal
systemctl start signal

# Check status
sleep 2
if systemctl is-active --quiet signal; then
    echo -e "${GREEN}✅ Signal service is running!${NC}"
    systemctl status signal --no-pager
else
    echo -e "${RED}❌ Signal service failed to start${NC}"
    journalctl -u signal --no-pager -n 20
    exit 1
fi

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status signal     # Check status"
echo "  sudo systemctl restart signal    # Restart service"
echo "  sudo systemctl stop signal       # Stop service"
echo "  sudo journalctl -u signal -f     # View logs"
echo "  sudo nano $DEPLOY_DIR/config.yaml  # Edit config"
