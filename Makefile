lib:
	(cd acto/k8s_util/lib && make)
	(cd ssa && make)

clean:
	(cd acto/k8s_util/lib && make clean)
	(cd ssa && make clean)
