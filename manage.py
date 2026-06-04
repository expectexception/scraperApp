#!/usr/bin/env python3
import os
import sys


def main():
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv', 'bin', 'python')
    if sys.executable != venv_python and os.path.exists(venv_python):
        os.execl(venv_python, venv_python, *sys.argv)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scraper_service.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
