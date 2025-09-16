
import os
import json

from colorama import Fore, Style, init as colorama_init

def list_result_files(results_dir="results"):
    files = []
    if not os.path.isdir(results_dir):
        print(f"No results directory found at '{results_dir}'.")
        return files
    for f in os.listdir(results_dir):
        if f.endswith(".json"):
            files.append(os.path.join(results_dir, f))
    return sorted(files)

def choose_file(files):
    if not files:
        print("No result files found.")
        return None
    print(f"{Style.BRIGHT}{Fore.LIGHTMAGENTA_EX}Available result files:{Style.RESET_ALL}")
    for idx, f in enumerate(files):
        print(f"  {Style.NORMAL}{Fore.YELLOW}[{idx+1}] {os.path.basename(f)} {Style.RESET_ALL}")
    while True:
        try:
            prompt = f"{Style.BRIGHT}{Fore.GREEN}Select a file [1-{len(files)}]: {Style.RESET_ALL}"
            choice = int(input(prompt))
            if 1 <= choice <= len(files):
                return files[choice-1]
        except Exception:
            pass
        print("Invalid selection. Please try again.")

def extract_provider_model(filepath):
    # Expects: <date>_<time>_<provider>_<model>.json
    fname = os.path.basename(filepath)
    parts = fname.split("_")
    if len(parts) < 4:
        return "unknown", "unknown"
    provider = parts[2]
    model = "_".join(parts[3:])[:-5]  # remove .json
    return provider, model

def create_format_statistics(json_file_path):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    format_name_to_statistics = {}
    for result in data['detailed_results']:
        format_name = result['format_name']
        if format_name not in format_name_to_statistics:
            format_name_to_statistics[format_name] = {'total': 0, 'correct': 0}
        format_name_to_statistics[format_name]['total'] += 1
        if result['format_correct']:
            format_name_to_statistics[format_name]['correct'] += 1
    for format_name, stats in format_name_to_statistics.items():
        total = stats['total']
        correct = stats['correct']
        stats['accuracy'] = correct / total if total > 0 else 0.0
    return format_name_to_statistics

def veiw_results(results_filepath: str) -> None:
    provider, model = extract_provider_model(results_filepath)
    format_stats = create_format_statistics(results_filepath)

    evaluation_summary_text = """
\n
▗▄▄▄▖▗▖  ▗▖ ▗▄▖ ▗▖   ▗▖ ▗▖ ▗▄▖▗▄▄▄▖▗▄▄▄▖ ▗▄▖ ▗▖  ▗▖     ▗▄▄▖▗▖ ▗▖▗▖  ▗▖▗▖  ▗▖ ▗▄▖ ▗▄▄▖▗▖  ▗▖
▐▌   ▐▌  ▐▌▐▌ ▐▌▐▌   ▐▌ ▐▌▐▌ ▐▌ █    █  ▐▌ ▐▌▐▛▚▖▐▌    ▐▌   ▐▌ ▐▌▐▛▚▞▜▌▐▛▚▞▜▌▐▌ ▐▌▐▌ ▐▌▝▚▞▘ 
▐▛▀▀▘▐▌  ▐▌▐▛▀▜▌▐▌   ▐▌ ▐▌▐▛▀▜▌ █    █  ▐▌ ▐▌▐▌ ▝▜▌     ▝▀▚▖▐▌ ▐▌▐▌  ▐▌▐▌  ▐▌▐▛▀▜▌▐▛▀▚▖ ▐▌  
▐▙▄▄▖ ▝▚▞▘ ▐▌ ▐▌▐▙▄▄▖▝▚▄▞▘▐▌ ▐▌ █  ▗▄█▄▖▝▚▄▞▘▐▌  ▐▌    ▗▄▄▞▘▝▚▄▞▘▐▌  ▐▌▐▌  ▐▌▐▌ ▐▌▐▌ ▐▌ ▐▌  
\n
"""
    print(f"{Fore.WHITE}{evaluation_summary_text}{Style.RESET_ALL}")

    print(f"{Fore.CYAN}{Style.BRIGHT}Provider:{Style.RESET_ALL} {Fore.YELLOW}{provider}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}Model:{Style.RESET_ALL} {Fore.YELLOW}{model}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}Results file:{Style.RESET_ALL} {Fore.YELLOW}{results_filepath}{Style.RESET_ALL}\n\n")

    print(f"{Fore.GREEN}{Style.BRIGHT}{'Format Name':<40} {'Total':>7} {'Correct':>9} {'Accuracy':>10}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'-'*40} {'-'*7} {'-'*9} {'-'*10}{Style.RESET_ALL}")

    total = 0
    correct = 0
    for fmt, stats in format_stats.items():
        total += stats['total']
        correct += stats['correct']
        acc = stats['accuracy']
        print(f"{Fore.WHITE}{fmt:<40} {stats['total']:>7} {stats['correct']:>9} {acc:>9.2%}{Style.RESET_ALL}")

    overall_acc = correct / total if total > 0 else 0.0
    print(f"{Style.BRIGHT}{Fore.MAGENTA}{'OVERALL':<40} {total:>7} {correct:>9} {overall_acc:>9.2%}{Style.RESET_ALL}\n\n")

def main():
    colorama_init()
    files = list_result_files()
    chosen = choose_file(files)
    if not chosen:
        return
    veiw_results(chosen)

if __name__ == "__main__":
    main()