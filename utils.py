import sys

def handle_failure(error_msg, context="Execution"):
    """
    Standardizes error handling across the application.
    Prompts the user to securely abort or confidently continue upon a trapped failure.
    """
    print(f"\n[!] A non-fatal error occurred during: {context}")
    print(f"    Error Details: {error_msg}")
    
    while True:
        try:
            choice = input(f"\nDo you want to (C)ontinue skipping this file/step, or (A)bort the run? (C/A): ").strip().lower()
            if choice in ['c', 'continue', 'y', 'yes', 'skip']:
                print("  [>] Proceeding with fallback...\n")
                return
            elif choice in ['a', 'abort', 'n', 'no', 'stop', 'quit', 'exit']:
                print("\n[!] Aborting sort process immediately due to explicit user command.")
                sys.exit(1)
            else:
                print("  Invalid selection. Please enter 'C' to continue, or 'A' to abort.")
        except (EOFError, KeyboardInterrupt):
            print("\n[!] Aborting sort process immediately.")
            sys.exit(1)
