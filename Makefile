.PHONY: test

test:
	poetry run flake8 && \
		poetry run coverage run --source=jsonrpcbase -m pytest test && \
		poetry run coverage report
