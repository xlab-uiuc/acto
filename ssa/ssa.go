package main

import (
	"fmt"
	"os"

	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func main() {
	// Load, parse, and type-check the whole program.
	cfg := packages.Config{
		Mode: packages.LoadAllSyntax,
		Dir:  "/home/tyler/zookeeper-operator",
	}
	initial, err := packages.Load(&cfg, "file=/home/tyler/zookeeper-operator/cmd/exporter/main.go")
	if err != nil {
		fmt.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, pkgs := ssautil.AllPackages(initial, 0)
	_ = pkgs

	// Build SSA code for the whole program.
	prog.Build()

	for _, pkg := range prog.AllPackages() {
		fmt.Println(pkg.String())
	}

	main_pkg := prog.ImportedPackage("github.com/pravega/zookeeper-operator/cmd/exporter")
	main_func := main_pkg.Members["main"].(*ssa.Function)
	fmt.Println(main_func)
	main_func.WriteTo(os.Stdout)

	zk_pkg := prog.ImportedPackage("github.com/pravega/zookeeper-operator/pkg/zk")
	generator_func := zk_pkg.Members["MakeStatefulSet"].(*ssa.Function)
	generator_func.WriteTo(os.Stdout)

	for _, blk := range generator_func.Blocks {
		for _, inst := range blk.Instrs {
			switch inst.(type) {
			case ssa.Call:

			}
		}
	}
}
