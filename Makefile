all:

check:
	pylint -e *.py
	python-coverage -e
	for i in *_test.py; do\
		echo $$i: ;\
		python-coverage -x $$i -v ;\
	done
	python-coverage -a *.py

clean:
	$(RM) *~ *,cover *.pyc

.PHONY: all clean check
