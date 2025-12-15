"""Entry point for running browser_controller as a module."""

if __name__ == "__main__":
    import sys

    from browser_controller.cli import main

    sys.exit(main())
