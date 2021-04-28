default: run

run:
	python main.py

deps:
	python -m pip install -r requirements.txt
	python setup.py install --user

test:
	python setup.py test

clean:
	rm -rf aquachain-kv.egg-info
	rm -rvf *.pyc */*.pyc */__pycache__ || true
	rm -rvf *.ini || true
	python setup.py clean

help:
	@printf 'aquachain gui wallet builder\n\n'
	@printf 'available targets:\n\n'
	@printf '\tmake deps\n\n'
	@printf '\tmake run\n\n'
	@printf '\tmake clean\n\n'
	@printf '\tmake install\n\n'

install:
	python setup.py install --user

onetest:
	python -m tests.test_keystore Test_Keystore.test_loadphrase
