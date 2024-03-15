.PHONY: analysis

analysis:
	go build -buildmode=c-shared -o libanalysis.so ssa.go

clean:
	rm -f ./analysis.so
