#!/usr/bin/env python3
"""
Universal inference script for evaluating LLMs on IFEval-FC data.

This script:
1. Loads test data from JSON files
2. Calls an LLM with user queries using universal LLM interface
3. Checks if the LLM calls the correct function
4. Validates parameter format using the appropriate checker
5. Scores the LLM's performance with binary scoring (1 if format followed, 0 if not)
"""

import argparse
import asyncio
from datetime import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
from colorama import Fore, Style
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolCall


# Local imports
from llm_factory import create_llm, load_env_file
from scripts.view_results import veiw_results
from IFEval_FC.checkers import get_all_checkers

# Different models are trained differently to call functions.
# For example, Claude is trained to make accurate, precise calls.
# When Claude encounters something unusual (such as a parameter with a format different from what the user provided), it asks for clarification.
# Other models, such as ChatGPT or GigaChat, tend to maximize recall and call functions regardless, which is an (unfair) advantage in this benchmark.
# Therefore, the following system message is used to instruct the model to ALWAYS call a function.

# Without this system message, models from OpenAI and Sber showed a function call rate close to 1, whereas the latest models from Anthropic showed rates of 0.7–0.8.
# Interestingly, older models like claude-3-5-haiku-20241022 also showed a very high function call rate (> 0.9), but the newer models (Opus 4.1) dramatically decreased this number.

# Despite this system message, claude-opus-4-1-20250805 does not fully comply:
# The function_called_rate is 0.9, which can reduce the final score by up to 10%.
# Further analysis revealed that enabling reasoning actually worsened this (an additional 6% of queries without a function call), though overall performance improved (71.60% vs 66.53%).

SYSTEM_MESSAGE = """
YOU MUST CALL A FUNCTION NO MATTER WHAT.
NEVER ASK A USER TO SPECIFY / CLARIFY ANYTHING.
ALWAYS CALL A FUNCTION.
""".strip()


class FunctionCallEvaluator:
    """
    Universal evaluator for LLM function calling capabilities on IFEval-FC data.
    """

    def __init__(self, provider: Optional[str] = None, **kwargs):
        """
        Initialize the evaluator with a specific LLM provider.
        All configuration is loaded from environment variables.

        Args:
            provider: LLM provider ('openai', 'anthropic', 'google', 'gigachat')
            **kwargs: Additional provider-specific arguments (will override env vars)
        """
        # Load environment variables
        load_env_file()

        # Initialize the LLM using the factory
        self.llm = create_llm(provider=provider, **kwargs)

        # Get provider and model info from environment
        self.provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        if self.provider is None:
            self.provider = "openai"
        self.model = os.getenv(f"{self.provider.upper()}_MODEL") or os.getenv(
            "DEFAULT_MODEL", "gpt-3.5-turbo"
        )

        # Get all available checkers
        self.checker_classes = {cls.__name__: cls for cls in get_all_checkers()}

        # Results storage
        self.results: List[Dict[str, Any]] = []

    def load_test_data(self, data_dir: str) -> List[Dict[str, Any]]:
        """
        Load all test data from JSON files in the data directory.

        Args:
            data_dir: Path to directory containing JSON test files

        Returns:
            List of test data dictionaries
        """
        data_path = Path(data_dir)
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory {data_dir} not found")

        test_files = list(data_path.glob("*.json"))
        if not test_files:
            raise FileNotFoundError(f"No JSON files found in {data_dir}")

        test_data = []
        for file_path in test_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    test_data.append(data)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse {file_path}: {e}")
                continue

        print(f"Loaded {len(test_data)} test files from {data_dir}")
        return test_data

    async def call_llm(self, user_queries: list[str], n_retries: int = 5) -> AIMessage:
        """
        Call the LLM with a user query.

        Args:
            user_query: The user's question

        Returns:
            LLM response as string
        """
        responses = None
        for _ in range(n_retries):
            try:
                # Create messages in a universal format
                chats = [
                    [SystemMessage(content=SYSTEM_MESSAGE), HumanMessage(content=user_query)] for user_query in user_queries
                ]

                responses = await self.llm.abatch(chats)
                assert responses is not None
                return responses
            except Exception as e:
                print(e)
                continue
        return [
            AIMessage(content=f"LLM.abatch() failed {n_retries} times.")
        ] * len(user_queries)

    def evaluate_response(
        self, test_data: Dict[str, Any], user_query: str, response: AIMessage
    ) -> Dict[str, Any]:
        """
        Evaluate a single response against the test data.

        Args:
            test_data: Test data containing expected function and format
            user_query: User query used to get the `response`
            response: AI response to the user query with content and tool calls

        Returns:
            Evaluation results dictionary
        """

        # Extract expected information
        expected_function = test_data["fn_schema"]["name"]
        chosen_param = test_data["chosen_param"]
        format_info = test_data["format"]
        format_name = format_info["name"]
        tool_calls: list[ToolCall] = response.tool_calls

        result = {
            "user_query": user_query,
            "expected_function": expected_function,
            "chosen_param": chosen_param,
            "format_name": format_name,
            "llm_response": {
                "content": response.content,
                "tool_calls": [
                    {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
                    for tc in (response.tool_calls or [])
                ],
            },
            "function_called": False,
            "parameter_provided": False,
            "format_correct": False,
            "overall_score": 0.0,
        }

        if not tool_calls:
            # No tool call detected
            result["function_called"] = False
            return result

        result["function_called"] = True

        # Check if the chosen parameter was provided (for every tool call)
        for tool_call in tool_calls:
            parameters = tool_call["args"]
            if chosen_param not in parameters:
                result["parameter_provided"] = False
                return result

        result["parameter_provided"] = True

        # Validate parameter format
        for tool_call in tool_calls:
            parameters = tool_call["args"]
            param_value = parameters[chosen_param]
            if isinstance(param_value, str):
                # Get the appropriate checker
                checker_class = self.checker_classes.get(format_name)
                if checker_class:
                    try:
                        # Create checker instance and validate
                        checker = checker_class()
                        # Set the checker's state to match the test data
                        checker.arguments = format_info.get("args", {})
                        checker.description = format_info.get("description", "")

                        format_correct = checker.check_following(param_value)
                        if not format_correct:
                            result["format_correct"] = False
                            return result
                    except Exception as e:
                        print(f"Error checking format {format_name}: {e}")
                        result["format_correct"] = False
                        return result
                else:
                    print(f"Warning: Checker {format_name} not found")
                    result["format_correct"] = False
                    return result
            else:
                result["format_correct"] = False
                return result

        result["format_correct"] = True

        # Calculate overall score: 1 if format is followed, 0 if not
        # Format is followed only if all conditions are met:
        # 1. Function is called
        # 2. Correct function is called
        # 3. Parameter is provided
        # 4. Format is correct
        if (
            result["function_called"]
            and result["parameter_provided"]
            and result["format_correct"]
        ):
            result["overall_score"] = 1.0
        else:
            result["overall_score"] = 0.0

        return result

    async def evaluate_all_data(
        self, data_dir: str, max_samples: Optional[int] = None, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all test data in the given directory.

        Args:
            data_dir: Path to directory containing test data
            max_samples: Maximum number of samples to evaluate (None for all)
            output_file: Path to output JSON file for incremental saving

        Returns:
            Summary evaluation results
        """
        # Load test data
        test_data_list = self.load_test_data(data_dir)

        if max_samples:
            test_data_list = test_data_list[:max_samples]

        all_results = []

        for i, test_data in enumerate(test_data_list):
            print(
                f"Evaluating test case {i+1}/{len(test_data_list)}: {test_data.get('fn_schema', {}).get('name', 'unknown')}"
            )

            user_queries = test_data.get("user_queries", [])
            if not user_queries:
                print(f"  Warning: No user queries found in test case {i+1}")
                continue

            # Call LLM
            # Evaluate each user query for this test case

            self.llm = self.llm.bind_tools([test_data["fn_schema"]])
            responses = await self.call_llm(user_queries)

            for j, (user_query, response) in enumerate(zip(user_queries, responses)):
                print(
                    f"{Style.BRIGHT}{Fore.CYAN}  Query {j+1}/{len(user_queries)}:{Style.RESET_ALL} {Fore.YELLOW}{Style.RESET_ALL}"
                )
                result = self.evaluate_response(test_data, user_query, response)
                result["test_case_id"] = i
                result["query_id"] = j
                if result.get("overall_score", 0.0) == 1.0:
                    print(f"{Fore.GREEN}{Style.BRIGHT}    ✔ Passed{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}{Style.BRIGHT}    ✘ Failed{Style.RESET_ALL}")
                all_results.append(result)

            # Print overall accuracy so far after each file
            num_evaluated = len(all_results)
            num_correct = sum(1 for r in all_results if r.get("overall_score", 0.0) == 1.0)
            accuracy = num_correct / num_evaluated if num_evaluated > 0 else 0.0
            print(f"{Style.BRIGHT}{Fore.MAGENTA}Overall accuracy after {i+1} file(s): {accuracy:.2%}{Style.RESET_ALL}")

            # Save results after each file
            if output_file:
                summary = self.calculate_summary_stats(all_results)
                summary["detailed_results"] = all_results
                self.save_results(summary, output_file)

        # Calculate summary statistics
        summary = self.calculate_summary_stats(all_results)
        summary["detailed_results"] = all_results

        return summary

    def calculate_summary_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics from evaluation results.

        Args:
            results: List of individual evaluation results

        Returns:
            Summary statistics dictionary
        """
        if not results:
            return {"error": "No results to summarize"}

        total_queries = len(results)
        function_called_count = sum(1 for r in results if r["function_called"])
        parameter_provided_count = sum(1 for r in results if r["parameter_provided"])
        format_correct_count = sum(1 for r in results if r["format_correct"])

        summary = {
            "total_queries": total_queries,
            "function_called_rate": function_called_count / total_queries,
            "parameter_provided_rate": parameter_provided_count / total_queries,
            "format_correct_rate": format_correct_count / total_queries,
            "function_called_count": function_called_count,
            "parameter_provided_count": parameter_provided_count,
            "format_correct_count": format_correct_count,
        }

        return summary

    def save_results(self, results: Dict[str, Any], output_file: str):
        """
        Save evaluation results to a JSON file.

        Args:
            results: Evaluation results dictionary
            output_file: Path to output JSON file
        """
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Universal LLM evaluation for function calling capabilities on IFEval-FC data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evaluate.py --data-dir data --provider openai --model gpt-3.5-turbo --output results.json
  python evaluate.py --data-dir data --provider anthropic --model claude-3-sonnet-20240229 --max-samples 10
  python evaluate.py --data-dir data --provider google --model gemini-pro --temperature 0.1
        """,
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.getenv("DATA_DIR", "data"),
        help="Directory containing test data JSON files (default: data)",
    )

    parser.add_argument(
        "--provider",
        type=str,
        default=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        choices=["openai", "anthropic", "google", "gigachat"],
        help="LLM provider to use (default: openai)",
    )

    parser.add_argument(
        "--model",
        type=str,
        help="Model name (if not specified, uses default from environment). Note: This will override the MODEL env var for the selected provider.",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        help="Model temperature (if not specified, uses default from environment). Note: This will override the TEMPERATURE env var for the selected provider.",
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        help="Maximum number of test samples to evaluate (default: all)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (default: results/<current_datetime>_<provider>_<model_name>.json)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    # Load environment variables
    load_env_file()
    args = parser.parse_args()

    # Fill output with default if not specified
    if args.output is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use model from args if provided, else from env, else from evaluator.model
        model_name = args.model or os.getenv(f"{args.provider.upper()}_MODEL")
        # Remove slashes or spaces from model name for filename safety
        model_name_safe = str(model_name).replace("/", "_").replace(" ", "_")
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        args.output = os.path.join(results_dir, f"{now}_{args.provider}_{model_name_safe}.json")

    # Prepare kwargs for any overrides
    kwargs = {}
    if args.model:
        kwargs["model"] = args.model
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature

    # Initialize evaluator
    evaluator = FunctionCallEvaluator(provider=args.provider, **kwargs)

    # Run evaluation
    print(f"Starting evaluation with provider: {args.provider}")
    print(f"Model: {evaluator.model}")
    print(f"Data directory: {args.data_dir}")
    if args.max_samples:
        print(f"Max samples: {args.max_samples}")

    try:
        results = await evaluator.evaluate_all_data(
            data_dir=args.data_dir, max_samples=args.max_samples, output_file=args.output
        )

        # Save results (final save to ensure latest state)
        evaluator.save_results(results, args.output)

        # Show metrics
        veiw_results(args.output)

    except Exception as e:
        print(f"Error during evaluation: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
