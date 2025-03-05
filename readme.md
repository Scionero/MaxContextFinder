# Ollama Context Size Tester

A tool to determine the maximum usable context size for Ollama models while monitoring performance and VRAM usage. This tool helps you find the optimal balance between context size and performance for your specific hardware setup.

## Overview

This tool tests increasing context sizes with your chosen Ollama model to find the maximum size that maintains acceptable performance. It monitors:
- Token processing speed (tokens per second)
- VRAM usage
- Response times
- Model behavior at different context lengths

## Prerequisites

### Windows
- Windows 10/11
- Python 3.8+
- Ollama (https://ollama.com/) installed and running
- For VRAM monitoring:
  - NVIDIA GPU: No additional setup needed (uses nvidia-smi, included with drivers)
  - AMD GPU: ROCm for Windows (if available for your GPU)

### Linux
- Python 3.8+
- Ollama installed and running
- For VRAM monitoring:
  - NVIDIA GPU: No additional setup needed (uses nvidia-smi)
  - AMD GPU: Either ROCm or radeontop (`sudo apt install radeontop` on Ubuntu/Debian)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/ollama-context-tester
cd ollama-context-tester
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
python main.py MODEL_NAME
```

Example:
```bash
python main.py codellama:latest
```

### Command Line Options

- `model`: (Required) The Ollama model name (e.g., 'codellama:latest', 'llama2:13b')
- `--min_token_rate`: Minimum acceptable tokens per second (default: 10)
- `--start`: Starting context size (default: 1024)
- `--step`: Step size for context increments (default: 1024)
- `--tests`: Number of tests per context size (default: 3)

Example with all options:
```bash
python main.py mistral:7b --min_token_rate 15 --start 2048 --step 2048 --tests 5
```

### Output

The tool generates detailed logs including:
- Test parameters and configuration
- Performance metrics for each test
- VRAM usage statistics (when available)
- Token processing speeds
- Final recommended context size

Logs are saved to the `logs` directory with names: `context_test_MODEL_TIMESTAMP.log`

## VRAM Monitoring Support

### Windows
- NVIDIA GPUs: Fully supported through nvidia-smi
- AMD GPUs: Supported through ROCm when available
- Intel GPUs: Not currently supported

### Linux
- NVIDIA GPUs: Fully supported through nvidia-smi
- AMD GPUs: Supported through either:
  - ROCm (preferred when available)
  - radeontop (fallback option)
- Intel GPUs: Not currently supported

## Important Notes

1. **GPU Support**: 
   - NVIDIA GPUs are fully supported on both Windows and Linux
   - AMD GPU support varies by platform and available tools
   - Systems without supported GPUs will run without VRAM monitoring

2. **Framework Specificity**: Results are specific to Ollama and may differ from other frameworks like:
   - Pure llama.cpp
   - vLLM
   - Different quantization methods
   - Other serving frameworks

3. **Hardware Dependence**: Results depend on your hardware:
   - GPU memory and performance
   - CPU capabilities
   - System memory
   - Storage speed

## Understanding Results

The tool stops testing larger context sizes when:
- Token processing speed drops below the minimum threshold
- VRAM usage approaches 100%
- Model encounters errors or timeouts

The "maximum recommended context size" is the largest size that maintained acceptable performance across all metrics.

## Contributing

Contributions are welcome! Areas for improvement:
- Additional GPU support
- More performance metrics
- Support for other frameworks
- Better token counting accuracy
- Alternative testing methodologies

Please feel free to:
- Open issues for bugs or feature requests
- Submit pull requests with improvements
- Share your testing results
- Suggest better testing methodologies

## Disclaimer

Results should be considered approximate. Real-world performance may vary based on:
- Specific prompt content
- Model implementation details
- System load and conditions
- Hardware configuration