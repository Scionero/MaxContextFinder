# Ollama Context Size Tester

A tool to determine the maximum usable context size for Ollama models while monitoring performance and VRAM usage. This tool helps you find the optimal balance between context size and performance for your specific hardware setup.

## Overview

This tool tests increasing context sizes with your chosen Ollama model to find the maximum size that maintains acceptable performance. It monitors:
- Token processing speed (tokens per second)
- VRAM usage
- Response times
- Model behavior at different context lengths

## Prerequisites

- Python 3.8+
- Ollama (https://ollama.ai/) installed and running
- Ollama models downloaded (You can use `ollama list` to find all your current models)
- For VRAM monitoring (AMD GPUs only):
  - radeontop installed (`sudo apt install radeontop` on Ubuntu/Debian)

## Installation

1. Clone this repository:

    git clone https://github.com/yourusername/ollama-context-tester
    cd ollama-context-tester

2. Install required Python packages:

    pip install ollama timeout-decorator

## Usage

Basic usage:

    python main.py MODEL_NAME

Example:

    python main.py codellama:latest

### Command Line Options

- `model`: (Required) The Ollama model name (e.g., 'codellama:latest', 'llama2:13b')
- `--min_token_rate`: Minimum acceptable tokens per second (default: 10)
- `--start`: Starting context size (default: 1024)
- `--step`: Step size for context increments (default: 1024)
- `--tests`: Number of tests per context size (default: 3)

Example with all options:

    python main.py mistral:7b --min_token_rate 15 --start 2048 --step 2048 --tests 5

### Output

The tool generates detailed logs including:
- Test parameters and configuration
- Performance metrics for each test
- VRAM usage statistics
- Token processing speeds
- Final recommended context size

Logs are saved to files named: `context_test_MODEL_TIMESTAMP.log`

## Important Notes

1. **Framework Specificity**: This tool tests context sizes specifically for Ollama. Results may differ significantly with other frameworks like:
   - Pure llama.cpp Python bindings
   - vLLM
   - Different quantization methods
   - Other serving frameworks

2. **Hardware Dependence**: Results are highly dependent on your specific hardware configuration:
   - GPU memory and performance
   - CPU capabilities
   - System memory
   - Storage speed

3. **VRAM Monitoring**: Currently supports AMD GPUs using radeontop. NVIDIA support might be added in the future.

## Understanding Results

The tool will stop testing larger context sizes when either:
- Token processing speed drops below the minimum threshold
- VRAM usage approaches 100%
- Model encounters errors or timeouts

The "maximum recommended context size" is the largest size that maintained acceptable performance across all metrics.

## Contributing

Contributions are welcome! Areas for potential improvement:
- NVIDIA GPU VRAM monitoring support
- Additional performance metrics
- Support for other frameworks
- Better token counting accuracy
- Alternative testing methodologies

Please feel free to:
- Open issues for bugs or feature requests
- Submit pull requests with improvements
- Share your testing results with different models/hardware
- Suggest better testing methodologies

## Disclaimer

Results from this tool should be considered approximate. Real-world performance may vary based on:
- Specific prompt content
- Model implementation details
- System load and conditions
- Hardware configuration