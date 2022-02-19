#
# https://makefiletutorial.com
#

SHELL := /bin/bash

.DEFAULT_GOAL = report

format:
	pdm run python -m black src tests

format-check:
	pdm run python -m black src tests --diff --check

lint:
	pdm run flake8 src tests

test:
	pdm run pytest

report:
	pdm run ibtax --year-report inputs/report.csv
