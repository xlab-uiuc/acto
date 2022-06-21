lib:
	(cd k8s_util/lib && make)
	(cd ssa && make)

clean:
	(cd k8s_util/lib && make clean)
	(cd ssa && make)