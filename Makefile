all: lib patch_module

lib:
	(cd acto/k8s_util/lib && make)
	(cd ssa && make)

patch_module:
	(cd monkey_patch && python setup.py install)

clean:
	(cd acto/k8s_util/lib && make clean)
	(cd ssa && make)