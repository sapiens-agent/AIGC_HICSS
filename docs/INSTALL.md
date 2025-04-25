# Installation and Usage Guide

## Table of Contents

- [Installation and Usage Guide](#installation-and-usage-guide)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Environment Setup](#environment-setup)
    - [1. Install Conda](#1-install-conda)
    - [2. Create and Activate Virtual Environment](#2-create-and-activate-virtual-environment)
    - [3. Install Dependencies](#3-install-dependencies)
  - [Environment Variables](#environment-variables)
  - [Azure OpenAI API Configuration](#azure-openai-api-configuration)
  - [ComfyUI Setup](#comfyui-setup)
    - [1. Install ComfyUI](#1-install-comfyui)
    - [2. Start ComfyUI Service](#2-start-comfyui-service)
  - [Launch and Access](#launch-and-access)
  - [Troubleshooting](#troubleshooting)
    - [Q: Getting Azure OpenAI 401 or 403 errors?](#q-getting-azure-openai-401-or-403-errors)
    - [Q: Cannot access ComfyUI page?](#q-cannot-access-comfyui-page)

## Introduction

This project integrates Azure OpenAI and ComfyUI, providing powerful inference and visual processing capabilities. This documentation will guide you through environment configuration, API integration, and service startup.

## Environment Setup

### 1. Install Conda

Visit the Conda official website to install Miniconda or Anaconda.

### 2. Create and Activate Virtual Environment

```bash
conda create -n AIGC python=3.10 -y
conda activate AIGC
```

### 3. Install Dependencies

Ensure that the `requirements.txt` file exists in the project root directory:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root directory with the following content:

```ini
# Log level options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# ComfyUI API Configuration
COMFYUI_BASE_API_URL=http://127.0.0.1:8188/api
COMFYUI_WEBSOCKET_API_URL=ws://127.0.0.1:8188/ws

# Azure OpenAI API Configuration
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2023-12-01-preview

# Default Batch Processing Settings (can keep default)
DEFAULT_BATCHSIZE_USE_ONE_PROMPT=1

# Product Image to Poster Settings (can keep default)
IMAGE2POSTER_BATCHSIZE_USE_ONE_PROMPT=1
IMAGE2POSTER_OUTPUT_SIZE_WIDTH=1024
IMAGE2POSTER_OUTPUT_SIZE_HEIGHT=1024
IMAGE2POSTER_SCALE_MIN=0.3
IMAGE2POSTER_SCALE_MAX=0.7
```

> 💡 Tip: Add `.env` to your `.gitignore` to prevent sensitive information exposure.

## Azure OpenAI API Configuration

1. Log in to Azure Portal
2. Create Azure OpenAI service
3. Deploy required models (e.g., gpt-4, gpt-35-turbo, or embedding models)
4. Obtain the following information:
   - API Key
   - Endpoint
   - API Version (recommend using the latest official version)
   - Deployment name (must match AZURE_OPENAI_MODEL)

## ComfyUI Setup

### 1. Install ComfyUI

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start ComfyUI Service

```bash
python main.py
```

Service addresses:
- Web Interface: http://127.0.0.1:8188
- API Endpoint: http://127.0.0.1:8188/api
- WebSocket Endpoint: ws://127.0.0.1:8188/ws

## Launch and Access

Ensure `.env` is configured and saved, and ComfyUI is running. Then run your main program:

```bash
python main.py
```

## Troubleshooting

### Q: Getting Azure OpenAI 401 or 403 errors?

- Verify that the API Key and Endpoint are correct and the corresponding model is enabled
- Check if the model name in `.env` matches the Azure deployment name

### Q: Cannot access ComfyUI page?

- Check if main.py is running
- Confirm that port 8188 is not occupied
- Check if firewall/security software is blocking access 