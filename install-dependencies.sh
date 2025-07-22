#!/bin/bash

echo "Installing system dependencies..."

# Install unzip if not present
sudo apt-get update
sudo apt-get install -y unzip curl

# Install AWS CLI
echo "Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Clean up
rm -rf awscliv2.zip aws/

# Install Python pip if not present
sudo apt-get install -y python3-pip python3-venv

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install Python dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Installation complete!"
echo "AWS CLI version:"
aws --version
echo ""
echo "To activate the virtual environment, run:"
echo "source venv/bin/activate"