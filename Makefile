install-dev-venv:
	rm -rf venv/dev && \
	python3 -m venv venv/dev && \
	source venv/dev/bin/activate && \
	brew list postgres &>/dev/null || brew install postgres && \
	pip install -U pip && \
	pip install -r requirements-dev.txt

# run it like "t=gitlab make discover"
discover:
	python app/discover.py -t $(t) && \
	singer-discover --input taps/tap-$(t)/catalog.json --output taps/tap-$(t)/catalog.json

# run it like "tap=adwords target=redshift make sync"
sync:
	python app/main.py --tap $(tap) --target $(target)
