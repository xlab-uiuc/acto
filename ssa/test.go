package main

import (
	"fmt"
	"go/types"
	"log"
	"sort"

	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func Main() {
	// Load, parse, and type-check the initial packages.
	cfg := &packages.Config{Mode: packages.LoadSyntax}
	initial, err := packages.Load(cfg, "golang.org/x/tools/go/ssa")
	if err != nil {
		log.Fatal(err)
	}

	// Stop if any package had errors.
	// This step is optional; without it, the next step
	// will create SSA for only a subset of packages.
	if packages.PrintErrors(initial) > 0 {
		log.Fatalf("packages contain errors")
	}

	// Create SSA packages for all well-typed packages.
	prog, pkgs := ssautil.Packages(initial, ssa.PrintPackages)

	// Build SSA code for the well-typed initial packages.
	for _, p := range pkgs {
		if p != nil {
			p.Build()
		}
	}

	ret := []*ssa.Type{}
	for _, pkg := range prog.AllPackages() {
		if pkg.Pkg.Name() == "ssa" {
			for _, m := range pkg.Members {
				switch typedMember := m.(type) {
				case *ssa.Type:
					ret = append(ret, typedMember)
				}
			}
		}
	}

	instInter := util.FindSeedType(prog, "Instruction")
	valueInter := util.FindSeedType(prog, "Value")
	fmt.Println(valueInter)
	fmt.Println(ret)

	instImplementation := []string{}
	valueImplementation := []string{}
	for _, typ := range ret {

		switch named := typ.Type().(type) {
		case *types.Named:
			fmt.Println(named.String())
			if types.Implements(named, instInter.Type().Underlying().(*types.Interface)) {
				instImplementation = append(instImplementation, named.Obj().Name())
			} else if types.Implements(types.NewPointer(named), instInter.Type().Underlying().(*types.Interface)) {
				instImplementation = append(instImplementation, named.Obj().Name())
			}

			if types.Implements(named, valueInter.Type().Underlying().(*types.Interface)) {
				valueImplementation = append(valueImplementation, named.Obj().Name())
			} else if types.Implements(types.NewPointer(named), valueInter.Type().Underlying().(*types.Interface)) {
				valueImplementation = append(valueImplementation, named.Obj().Name())
			}
		default:
			// fmt.Printf("Type %T\n", named)
		}
	}

	sort.Strings(valueImplementation)
	for _, impl := range valueImplementation {
		fmt.Println(impl)
	}
}

func Implements(t *types.Named, itfc *types.Interface) bool {
	for i := 0; i < itfc.NumMethods(); i++ {
		method := itfc.Method(i)
		// fmt.Println(method.Name())
		obj, _, _ := types.LookupFieldOrMethod(t, true, t.Obj().Pkg(), method.Name())
		if obj == nil {
			fmt.Printf("%s does not implement because Method %s not implemented\n", t.Obj().Name(), method.Name())
			return false
		}
	}
	return true
}
