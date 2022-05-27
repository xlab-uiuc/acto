package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/xlab-uiuc/acto/ssa/analysis"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa/ssautil"
)

func main() {
	// Load, parse, and type-check the whole program.

	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	flag.Parse()

	cfg := packages.Config{
		Mode: packages.LoadAllSyntax,
		Dir:  *projectPath,
	}
	initial, err := packages.Load(&cfg, ".")
	if err != nil {
		fmt.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()

	valueFieldSetMap := analysis.GetValueToFieldMappingPass(prog, *seedType)

	valueFieldSetMapFile, err := os.Create("mapping.txt")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to create mapping.txt to write mapping: %s\n", err)
	}
	defer valueFieldSetMapFile.Close()

	for v, path := range valueFieldSetMap {
		fmt.Fprintf(valueFieldSetMapFile, "Path %s at [%s] [%s]=[%s] \n", path.Fields(), v.Parent(), v.Name(), v.String())
	}
	fmt.Println("------------------------")
}
