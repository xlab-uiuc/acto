k8sutil:
	go build -buildmode=c-shared -o k8sutil.so k8sutil.go
	gcc test.c -o test ./k8sutil.so

clean:
	rm ./k8sutil.so
	rm ./test