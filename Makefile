.PHONY: test

test:
	poetry run flake8
	poetry run nosetests
