"""Terminal presentation only: colours, tables, pagination."""
import os

if os.name == "nt":
    os.system("")  # enables ANSI colours on Windows terminals
RED, GREEN, YELLOW, CYAN, BOLD, DIM, RESET = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[2m", "\033[0m"


def banner():
    print(f"""{RED}{BOLD}
  +----------------------------------------------+
  |   FIRST-AID INFORMATION FINDER   (+)         |
  |   Campus Catalyst  |  Health & Wellbeing     |
  +----------------------------------------------+{RESET}
{DIM}  Educational tool. In an emergency, call your local emergency number.{RESET}
""")


def sev_colour(sev):
    return GREEN if sev <= 2 else YELLOW if sev == 3 else RED


def print_table(entries):
    line = "+-----+" + "-" * 36 + "+" + "-" * 22 + "+-----+-------+-------+"
    print(line)
    print(f"| {'ID':<3} | {'Title':<34} | {'Category':<20} | Sev | 911?  | Views |")
    print(line)
    for e in entries:
        print(f"| {e.id:<3} | {e.title[:34]:<34} | {e.category[:20]:<20} | "
              f"{sev_colour(e.severity)}{e.severity:^3}{RESET} | {'YES' if e.call_emergency else 'no':<5} | {e.times_viewed:>5} |")
    print(line)


def paginate(entries, page_size):
    if not entries:
        print(f"{YELLOW}No matching records.{RESET}")
        return
    for start in range(0, len(entries), page_size):
        print_table(entries[start:start + page_size])
        end = min(start + page_size, len(entries))
        print(f"{DIM}Showing {start + 1}-{end} of {len(entries)}{RESET}")
        if end < len(entries) and input("Enter = next page, q = stop: ").strip().lower() == "q":
            break


def show_entry(e):
    print(f"\n{BOLD}{e.title}{RESET}  {DIM}(#{e.id}){RESET}")
    print(f"Category : {e.category}\nSeverity : {sev_colour(e.severity)}{e.severity}/5{RESET}")
    print(f"Keywords : {', '.join(e.keywords)}\nReviewed : {e.last_reviewed}")
    if e.call_emergency:
        print(f"{RED}{BOLD}!! CALL EMERGENCY SERVICES !!{RESET}")
    print("\nSteps:")
    for i, step in enumerate(e.step_list, 1):
        print(f"  {i}. {step}")
    print()
