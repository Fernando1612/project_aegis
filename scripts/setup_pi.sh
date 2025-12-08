#!/bin/bash

# Project AEGIS - Raspberry Pi Setup Script
# Installs Docker, ZRAM, and prepares directories.

set -e

echo ">>> Starting Project AEGIS Setup..."

# 1. Update System
echo ">>> Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install ZRAM (Memory Optimization)
echo ">>> Installing and configuring ZRAM..."
if ! command -v zramctl &> /dev/null; then
    sudo apt install -y zram-tools
    echo "PERCENT=50" | sudo tee -a /etc/default/zramswap
    sudo service zramswap reload
else
    echo ">>> ZRAM already installed."
fi

# 3. Install Docker
echo ">>> Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
    echo ">>> Docker installed. You may need to logout and login again for group changes to take effect."
else
    echo ">>> Docker already installed."
fi

# 4. Install Docker Compose
echo ">>> Installing Docker Compose..."
sudo apt install -y docker-compose-plugin

# 5. Create Directories
echo ">>> Creating project directories..."
mkdir -p freqtrade/user_data
mkdir -p aegis_brain

echo ">>> Setup Complete! Please reboot your Pi."
