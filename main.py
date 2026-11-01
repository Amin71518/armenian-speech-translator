"""Run directly in PyCharm with the project's Poetry interpreter."""

if __name__ == '__main__':
    import os
    from pathlib import Path

    os.chdir(Path(__file__).resolve().parent)
    from armenian_speech.launcher import main

    raise SystemExit(main())
