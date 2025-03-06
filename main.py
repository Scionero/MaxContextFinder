import argparse
import time
import statistics
import logging
from datetime import datetime
from typing import Tuple
import ollama
from ollama import GenerateResponse
from functools import wraps
import timeout_decorator
from vram_usage import get_vram_info

import os


def setup_logging(model_name: str) -> str:
    """Setup logging configuration and return the log filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"context_test_{model_name}_{timestamp}.log"

    # Ensure the logs directory exists
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

    return log_path


def timeout_handler(signum, frame):
    raise TimeoutError("Query timed out")


def retry_on_timeout(max_retries=3, timeout_seconds=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    # Set the timeout
                    @timeout_decorator.timeout(timeout_seconds)
                    def run_with_timeout():
                        return func(*args, **kwargs)

                    return run_with_timeout()

                except (TimeoutError, timeout_decorator.TimeoutError) as e:
                    logging.warning(f"Attempt {attempt + 1}/{max_retries} timed out after {timeout_seconds} seconds")
                    if attempt == max_retries - 1:
                        raise TimeoutError(f"All {max_retries} attempts timed out")
                    logging.info("Retrying...")
                    time.sleep(1)  # Brief pause before retry

            return None  # Should never reach here due to raise in last attempt

        return wrapper

    return decorator


def analyze_test_sentence() -> Tuple[str, int]:
    """Return the test sentence and its actual token count."""
    test_sentence = "This is a test sentence to measure context performance. "

    # Actual tokens (approximately):
    # "This" = 1
    # "is" = 1
    # "a" = 1
    # "test" = 1
    # "sentence" = 1
    # "to" = 1
    # "measure" = 1
    # "context" = 1
    # "performance" = 1
    # "." = 1
    # " " = several tokens, roughly 1-2 additional tokens

    actual_tokens = 11  # More accurate token count

    return test_sentence, actual_tokens


def generate_test_prompt(context_size: int) -> Tuple[str, int, int]:
    """Generate prompt and return prompt, its token count, and repetitions."""
    base_prompt = "Count the number of characters in the following text and explain your counting process. Here's the text:\n\n"
    # Base prompt tokens:
    # Approximately 15-17 tokens for the base prompt
    base_prompt_tokens = 16

    test_sentence, tokens_per_sentence = analyze_test_sentence()

    # Calculate how many repetitions we can fit
    available_tokens = context_size - base_prompt_tokens
    repetitions = max(1, available_tokens // tokens_per_sentence)

    repeated_text = test_sentence * repetitions
    full_prompt = base_prompt + repeated_text

    total_tokens = base_prompt_tokens + (repetitions * tokens_per_sentence)

    return full_prompt, total_tokens, repetitions


@retry_on_timeout(max_retries=3, timeout_seconds=args.timeout)
def run_ollama_query(model: str, context_size: int) -> Tuple[GenerateResponse, str, int]:
    """Run a query to Ollama with a specific context size and return the response metrics."""
    try:
        full_prompt, estimated_tokens, repetitions = generate_test_prompt(context_size)

        logging.debug(f"Estimated tokens in prompt: {estimated_tokens}")
        logging.debug(f"Number of repetitions: {repetitions}")

        client = ollama.Client(host='http://localhost:11434')  # Explicit host
        response = client.generate(
            model=model,
            prompt=full_prompt,
            options={
                "num_ctx": context_size
            }
        )
        return response, full_prompt, estimated_tokens
    except ConnectionError as e:
        logging.error(f"Failed to connect to Ollama server: {str(e)}")
        logging.info("Make sure Ollama is running and accessible at http://localhost:11434")
        raise


def calculate_tokens_per_second(response: GenerateResponse) -> float:
    """Calculate the tokens per second rate from the Ollama response."""
    eval_count = response.eval_count if hasattr(response, 'eval_count') else 0
    eval_duration = response.eval_duration if hasattr(response, 'eval_duration') else 1
    tokens_per_second = eval_count / (eval_duration * 1e-9)
    return tokens_per_second

def test_context_size(model: str, context_size: int, num_tests: int = 3) -> tuple[float, float, float]:
    """Run multiple tests at a specific context size and return the average tokens/sec and VRAM info."""
    tokens_per_second_list = []

    logging.info(f"\nContext Size: {context_size}")
    logging.info("-" * 50)

    # Get initial VRAM reading
    current_vram, max_vram = get_vram_info()
    logging.info(f"Initial VRAM Usage: {current_vram:.0f}M / {max_vram:.0f}M ({(current_vram/max_vram*100):.1f}%)")

    for i in range(num_tests):
        try:
            response, prompt, estimated_tokens = run_ollama_query(model, context_size)
            tokens_per_second = calculate_tokens_per_second(response)
            tokens_per_second_list.append(tokens_per_second)

            # Get VRAM reading after test
            current_vram, max_vram = get_vram_info()
            vram_percent = (current_vram / max_vram * 100) if max_vram > 0 else 0

            # Log detailed test information
            test_info = {
                "Test Number": i + 1,
                "Prompt Length (chars)": len(prompt),
                "Prompt Tokens": estimated_tokens,
                "Response Length (chars)": len(response.response),
                "Response Words": len(response.response.split()),
                "Response Estimated Tokens": int(len(response.response.split()) * 1.3),
                "Total Tokens Processed": response.eval_count,
                "Tokens/sec": f"{tokens_per_second:.2f}",
                "Eval Duration": f"{response.eval_duration * 1e-9:.2f}s",
                "VRAM Usage": f"{current_vram:.0f}M / {max_vram:.0f}M ({vram_percent:.1f}%)"
            }

            logging.info(f"Test {i + 1} Details:")
            for key, value in test_info.items():
                logging.info(f"  {key}: {value}")

            logging.info("Prompt Preview (first 200 chars):")
            logging.info(f"  {prompt[:200]}...")
            logging.info("Response Preview (first 200 chars):")
            logging.info(f"  {response.response[:200]}...\n")

        except (TimeoutError, ollama.ResponseError) as e:
            logging.error(f"Error in test {i + 1}: {str(e)}")
            continue

    if tokens_per_second_list:
        avg_tokens_per_second = statistics.mean(tokens_per_second_list)
        logging.info(f"Average tokens/sec for context size {context_size}: {avg_tokens_per_second:.2f}")
        return avg_tokens_per_second, current_vram, max_vram
    else:
        logging.warning(f"All tests failed for context size {context_size}")
        return 0.0, current_vram, max_vram


def find_max_context(model: str, start_size: int = 1024, step_size: int = 1024,
                     minimum_token_rate: int = 10, num_tests: int = 3) -> Tuple[int, float]:
    """Find the maximum context size for a model that maintains acceptable performance."""
    context_size = start_size
    previous_context_size = start_size
    previous_tokens_per_second = float('inf')

    logging.info(f"Starting maximum context size test for model: {model}")
    logging.info(f"Parameters:")
    logging.info(f"  Minimum acceptable token rate: {minimum_token_rate} tokens/sec")
    logging.info(f"  Starting context size: {start_size}")
    logging.info(f"  Step size: {step_size}")
    logging.info(f"  Tests per context size: {num_tests}")
    logging.info("=" * 50)

    while True:
        try:
            logging.info(f"\nTesting context size: {context_size}")
            avg_tokens_per_second, current_vram, max_vram = test_context_size(model, context_size, num_tests)
            vram_percent = (current_vram / max_vram * 100) if max_vram > 0 else 0

            # Check both token rate and VRAM usage
            is_good = avg_tokens_per_second >= minimum_token_rate and vram_percent < 99
            status = "GOOD" if is_good else "SLOW/HIGH VRAM"

            logging.info(f"Status: {status}")
            logging.info(f"Token Rate: {avg_tokens_per_second:.2f} tokens/sec")
            logging.info(f"VRAM Usage: {current_vram:.0f}M / {max_vram:.0f}M ({vram_percent:.1f}%)")

            if not is_good:
                reason = []
                if avg_tokens_per_second < minimum_token_rate:
                    reason.append(f"Token rate below minimum threshold of {minimum_token_rate}")
                if vram_percent >= 99:
                    reason.append("VRAM usage too high")
                logging.info(f"Stopping due to: {', '.join(reason)}")
                return previous_context_size, previous_tokens_per_second

            previous_context_size = context_size
            previous_tokens_per_second = avg_tokens_per_second
            context_size += step_size

        except ollama.ResponseError as e:
            logging.error(f"Error occurred at context size {context_size}: {str(e)}")
            return previous_context_size, previous_tokens_per_second


def run_context_test(model: str, min_token_rate: int = 10, start: int = 1024,
                     step: int = 1024, tests: int = 3) -> None:
    """
    Run the context size test with the given parameters and log results.

    Args:
        model: The Ollama model name
        min_token_rate: Minimum acceptable tokens per second
        start: Starting context size
        step: Step size for context increments
        tests: Number of tests per context size
    """
    # Setup logging
    log_filename = setup_logging(model)
    logging.info(f"Log file created: {log_filename}")

    max_context, final_tokens_per_second = find_max_context(
        model, start, step, min_token_rate, tests
    )

    # Log final results
    logging.info("\n" + "=" * 60)
    logging.info("FINAL RESULTS:")
    logging.info(f"Maximum recommended context size: {max_context}")
    logging.info(f"Average tokens per second at max context: {final_tokens_per_second:.2f}")
    logging.info(f"Minimum token rate threshold: {min_token_rate}")
    logging.info("=" * 60)

    # Also print to console
    print(f"\nResults have been saved to: {log_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find the maximum usable context size for an Ollama model")
    parser.add_argument("model", help="The Ollama model name (e.g., 'codestral:latest')")
    parser.add_argument("--min_token_rate", type=int, default=10,
                        help="The minimum acceptable tokens per second rate (default: 10)")
    parser.add_argument("--start", type=int, default=1024, help="Starting context size")
    parser.add_argument("--step", type=int, default=1024, help="Step size for context increments")
    parser.add_argument("--tests", type=int, default=3, help="Number of tests per context size")
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in seconds for retry mechanism')
    
    args = parser.parse_args()
    run_context_test(**vars(args))
